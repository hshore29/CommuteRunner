from datetime import time, datetime, timedelta
from pymongo import MongoClient
import requests
import sqlite3
import json

from google_apis import API_KEY
from transit_mapping import *
MAPS_URL = 'https://maps.googleapis.com/maps/api/'

# Directions API Allowed inputs
MODES = ['driving', 'transit', 'walking', 'bicycling']
TRANSIT_MODES = ['bus', 'subway', 'train', 'tram', 'rail']
TRANSIT_PREFS = ['less_walking', 'fewer_transfers']

# Connect to SQLite & MongoDB
sql = sqlite3.connect('Census Data/census.db')
cur = sql.cursor()

mongo = MongoClient('localhost', 27017)
mongodb = mongo.commute_runner

def utc_timestamp(hour, minutes):
    # Always choose next Wednesday
    today = datetime.now().date()
    today = datetime.combine(today, time(hour, minutes))
    delta = (2 - today.weekday()) % 7
    today = today + timedelta(days=delta)
    return today.strftime('%s')

def call_directions_api(origin, destination, mode='driving', **kwargs):
    # Unused API Parameters
    # alternatives: defaults to False
    # waypoints: pipe-separated list of waypoints
    # avoid: pipe-separated combination of tolls, highways, ferries, indoor
    # units: metric or imperial (only impacts display text)
    # region: override default region
    # transit_routing_preference: bias towards less_walking or fewer_transfers
    args = {
        'key': API_KEY,
        'origin': origin,
        'destination': destination
    }

    # Set Mode
    if mode in MODES:
        args['mode'] = mode

    # Set Traffic Model
    traffic_model = kwargs.get('traffic_model')
    if traffic_model and traffic_model in ('pessimistic', 'optimistic'):
        args['traffic_model'] = traffic_model

    # Transit-specific arguments
    if mode == 'transit':
        # Add either arrival or departure time
        arrive = kwargs.get('arrival_time')
        depart = kwargs.get('departure_time')
        if arrive and depart:
            raise TypeError('Arrival and Departure time both specified')
        elif arrive:
            args['arrival_time'] = arrive
        elif depart:
            args['departure_time'] = depart

        # Bias towards different Transit Modes
        transit_mode = kwargs.get('transit_mode')
        if transit_mode:
            if type(transit_mode) is not list:
                raise TypeError('Transit Mode must be list')
            transit_mode = [m for m in transit_mode if m in TRANSIT_MODES]
            if transit_mode:
                args['transit_mode'] = '|'.join(transit_mode)
        transit_pref = kwargs.get('transit_routing_preference')
        if transit_pref in TRANSIT_PREFS:
            args['transit_routing_preference'] = transit_pref

    # Request route
    r = requests.get(MAPS_URL + 'directions/json', params=args)
    return r.json()

def parse_directions(api_response):
    route = api_response['routes']
    data = dict()

    # Did we find routes?
    if not route:
        return {
            'status': 'NO_ROUTES',
            'description': 'No routes found',
            'overview': {'duration': None}
            }
    else:
        data['status'] = 'OK'
        route = route[0]

    # Overview information
    overview = dict()
    overview['polyline'] = route['overview_polyline']['points']

    route = route['legs'][0]
    if 'arrival_time' in route:
        overview['arrival_time'] = route['arrival_time']['value']
        overview['departure_time'] = route['departure_time']['value']
    overview['duration'] = route['duration']['value'] / 60
    overview['startend'] = [
        [route['start_location']['lng'], route['start_location']['lat']],
        [route['end_location']['lng'], route['end_location']['lat']]
        ]
    overview['end_address'] = route['end_address']
    overview['start_address'] = route['start_address']

    data['overview'] = overview

    # Step Line
    data['steps'] = list()
    for s in route['steps']:
        step = dict()

        # Common attributes
        step['travel_mode'] = s['travel_mode']
        step['duration'] = s['duration']['value'] / 60
        step['description'] = s['html_instructions']
        step['polyline'] = s['polyline']['points']
        step['startend'] = [
            [s['start_location']['lng'], s['start_location']['lat']],
            [s['end_location']['lng'], s['end_location']['lat']]
            ]

        # Remove zero length transfer steps
        if s['distance']['value'] == 0:
            continue

        # If mode is transit, Walking and Driving steps will have a more
        # detailed inner steps array, but we don't really need it
        # These steps have "manuevers" which are interesting, but too detailed

        # Transit attributes
        if s['travel_mode'] == 'TRANSIT':
            transit = dict()
            t = s['transit_details']

            # Overview
            transit['departure_stop'] = t['departure_stop']['name']
            transit['arrival_stop'] = t['arrival_stop']['name']
            transit['headsign'] = t['headsign']
            transit['num_stops'] = t['num_stops']

            # Line Info
            transit['line_name'] = t['line'].get('name')
            transit['line_short_name'] = t['line'].get('short_name')
            transit['transit_type'] = t['line']['vehicle']['type']

            # Agency Info
            transit['full_agency'] = None
            if 'agencies' in t['line']:
                transit['full_agency'] = t['line']['agencies'][0]['name']
            transit['agency'] = AGENCY_MAPPING.get(transit['full_agency'])

            # Line Color
            transit['mode_color'] = MODE_COLORS.get(transit['transit_type'])
            transit['agency_color'] = AGENCY_COLORS.get(transit['agency'])
            line_color = t['line'].get('color')
            if transit['agency'] not in KEEP_LINES:
                line_color = transit['agency_color']
            if line_color is None:
                if transit['agency'] in LINE_COLORS:
                    line = transit['line_short_name'] or transit['line_name']
                    line_color = LINE_COLORS[transit['agency']].get(line)
                else:
                    line_color = transit['agency_color']
            transit['line_color'] = line_color

            step['transit'] = transit
        
        data['steps'].append(step)

    # Step Summary Statistics
    step_modes = sorted(set(s['travel_mode'] for s in data['steps']))
    step_types = sorted(set(s['transit']['transit_type'] for s in data['steps']
                            if s['travel_mode'] == 'TRANSIT'))
    step_duration = sum(s['duration'] for s in data['steps'])

    data['overview']['step_modes'] = ','.join(step_modes)
    data['overview']['step_types'] = ','.join(step_types)
    data['overview']['step_duration'] = step_duration

    # If the commute is all walking, consolidate steps
    if data['overview']['step_modes'] == 'WALKING':
        data['steps'] = [{
            'travel_mode': 'WALKING_ONLY',
            'duration': data['overview']['duration'],
            'polyline': data['overview']['polyline'],
            'startend': data['overview']['startend'],
            'description': '',
            }]

    # If the commute is zero duration, it's the same start & end zip
    # Remove the steps and override the duration to 7 minutes
    if data['overview']['duration'] == 0:
        data['steps'] = list()
        data['overview']['duration'] = 7

    # If the commute includes a transit agency without detailed routes,
    # remove the steps (but keep summary stats)
    # These render as straight lines from stop to stop on the map
    if any(s['transit']['full_agency'] in LOW_DETAIL
           for s in data['steps'] if 'transit' in s):
        data['steps'] = list()

    return data

def populate_zipcode_latlon(zip_code):
    # Get geocoding from MongoDB
    doc = mongodb.geocoding.find_one({'_id': zip_code})

    # If there wasn't one, call the API
    if not doc or 'google' not in doc:
        _id = {'_id': zip_code}
        doc = doc or _id
        args = {
            'key': API_KEY,
            'address': zip_code,
            }
        r = requests.get(MAPS_URL + 'geocode/json', params=args)
        data = r.json()
        if data['status'] == 'OK':
            doc['google'] = {
                'lat': data['results'][0]['geometry']['location']['lat'],
                'lng': data['results'][0]['geometry']['location']['lng']
                }
            mongodb.geocoding.replace_one(_id, doc, True)

    return doc

def get_zipcode_latlon(zip_code):
    # Get geocoding from MongoDB
    doc = mongodb.geocoding.find_one({'_id': zip_code})
    if doc is None:
        raise Exception('Missing zip code: ' + zip_code)
    geo = doc.get('custom', doc.get('centroid', doc['google']))
    return str(geo['lat']) + ',' + str(geo['lng'])

def skip_zip(zip_code):
    if zip_code[0] not in ('0', '1'):
        return True
    if zip_code[0:2] not in ('06', '07', '08', '10', '11', '12', '18', '19'):
        return True
    if zip_code[0:3] in ('120', '121', '122', '123', '128', '129', '197',
                         '198', '199'):
        return True
    return False

def get_directions(work_zip):
    # Get list of zip pairs from DB
    cur.execute("""
        select ZCTA5, RESIDENCE_ZIP
        from ZIP_DATA d
          join ZIP_WEIGHTS w on d.FIPS_CODE = w.PLACE_OF_WORK_CODE
        where d.ZCTA5 = '%s' and (WEIGHT*EMP) >= 1
        order by WEIGHT*EMP desc""" % work_zip)
    home_zips = [z[1] for z in cur.fetchall()]

    # Set list of arrival times
    arrival_times = [(9, 0)] # (8, 30), (9, 30)

    # Set list of modes
    travel_modes = ['transit'] # 'driving', 'drive_transit'

    # Get MongoDB collection
    col = mongodb.directions
    
    # Loop through commute keys
    keys = ({'start': h, 'end': work_zip, 'arrive_by': a, 'mode': m}
            for h in home_zips for a in arrival_times for m in travel_modes)
    for k in keys:
        if col.find_one({'_id': k}):
            continue
        if skip_zip(k['start']):
            continue
        args = {
            'origin': get_zipcode_latlon(k['start']),
            'destination': get_zipcode_latlon(k['end']),
            'arrival_time': utc_timestamp(*k['arrive_by']),
            }
        if k['mode'] == 'transit':
            args['mode'] = 'transit'
            args['transit_mode'] = ['fewer_transfers']
        commute = call_directions_api(**args)
        col.insert_one({'_id': k, 'response': commute})

def clean_directions():
    # Get MongoDB collections
    raw = mongodb.directions
    clean = mongodb.commutes

    for doc in raw.find():
        if clean.find_one({'_id': doc['_id']}):
            continue
        commute = parse_directions(doc['response'])
        clean.insert_one({'_id': doc['_id'], 'commute': commute})
