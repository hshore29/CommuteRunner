from datetime import time, datetime, timedelta
from pymongo import MongoClient
import requests
import sqlite3
import json

unpolyline = lambda p: list(map(list, map(reversed, polyline.decode(p))))

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
    j = r.json()
    if j['status'] in ('OK', 'ZERO_RESULTS'):
        return j
    else:
        raise Exception('API Error: ' + j['status'] + ' for ' + \
                        origin + '-' + destination)

def parse_directions(api_response):
    route = api_response['routes']

    # Did we find routes?
    if not route:
        return {
            'status': 'NO_ROUTES',
            'description': 'No routes found',
            'overview': {'duration': None}
            }

    # Set up data dict
    data = {
        'status': 'OK',
        'overview': dict(),
        'steps': list()
        }
    over = data['overview']

    # Overview Information
    first = route[0]['legs'][0]
    last = route[-1]['legs'][0]
    if 'arrival_time' in last:
        over['arrival_time'] = last['arrival_time']['value']
    if 'departure_time' in first:
        over['departure_time'] = first['departure_time']['value']
    over['startend'] = [
        [first['start_location']['lng'], first['start_location']['lat']],
        [last['end_location']['lng'], last['end_location']['lat']]
        ]
    over['end_address'] = last.get('end_address')
    over['start_address'] = first.get('start_address')
    over['duration'] = 0

    # Go through routes
    for r in route:
        poly = r['overview_polyline']['points']

        leg = r['legs'][0]
        over['duration'] += leg['duration']['value'] / 60

        # Check step types
        # If the commute is all walking or driving, consolidate steps
        modes = ','.join(sorted(set(s['travel_mode'] for s in leg['steps'])))
        if modes in ('WALKING', 'DRIVING'):
            data['steps'].append({
                'travel_mode': modes + '_ONLY',
                'duration': leg['duration']['value'] / 60,
                'polyline': poly,
                'startend': [
                    [leg['start_location']['lng'], leg['start_location']['lat']],
                    [leg['end_location']['lng'], leg['end_location']['lat']]
                    ],
                'description': '',
                })
            continue
        
        for s in leg['steps']:
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
            # These steps have "manuevers" which are interesting,
            # but too detailed

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

def parse_nearby_response(zip_code, response):
    stations = list()
    if response['status'] == 'OK':
        for res in response['results']:
            s = dict()
            s['geo'] = res['geometry']['location']
            s['name'] = res['name']
            s['types'] = res['types']
            # If we're in Jersey, skip stations east of the hudson
            if zip_code[:2] in ('07', '08') and \
               s['geo']['lng'] >= -74.012:
                continue
            stations.append(s)
    return stations

def get_nearby_stations(zip_code, **kwargs):
    # Check mongo for saved stations
    doc = mongodb.stations.find_one({'_id': zip_code})
    if doc is not None:
        return doc

    # Get nearby train stations
    args = {
        'key': API_KEY,
        'location': get_zipcode_latlon(zip_code),
        'rankby': 'distance',
        'type': 'train_station|subway_station'
        }

    # Request places
    r = requests.get(MAPS_URL + 'place/nearbysearch/json', params=args)
    data = r.json()
    stations = parse_nearby_response(zip_code, data)

    # If we didn't find any, try again for all transit stations
    if not stations:
        args['type'] = 'transit_station'
        r = requests.get(MAPS_URL + 'place/nearbysearch/json', params=args)
        data = r.json()
        stations = parse_nearby_response(zip_code, data)

    # Save it in Mongo
    doc = {'_id': zip_code, 'stations': stations[:3]}
    mongodb.stations.insert_one(doc)
    return doc

def transit_zip(zip_code):
    if zip_code in ('07030', '07307', '07087', '07086', '07093', '10301'
                    '11692', '11691'):
        return True
    if zip_code in ('11414', '11356', '11357', '11360', '11361', '11362',
                    '11363', '11364', '11426', '10464', '10465'):
        return False
    zip_pre = zip_code[:3]
    return zip_pre in ('100', '101', '102', '104', '111', '112', '113', '114')

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
        select ZCTA5, RESIDENCE_ZIP, WEIGHT*EMP
        from ZIP_DATA d
          join ZIP_WEIGHTS w on d.FIPS_CODE = w.PLACE_OF_WORK_CODE
        where d.ZCTA5 = '%s' and (WEIGHT*EMP) >= 1
        order by WEIGHT*EMP desc""" % work_zip)
    home_zips = {z[1]: z[2] for z in cur.fetchall()}

    # Set list of arrival times
    arrival_times = [(9, 0)] # (8, 30), (9, 30)

    # Set list of modes
    travel_modes = ['transit', 'drive_transit']

    # Get MongoDB collection
    col = mongodb.directions
    
    # Loop through commute keys
    keys = ({'start': h, 'end': work_zip, 'arrive_by': a, 'mode': m}
            for h in home_zips for a in arrival_times for m in travel_modes)
    for k in keys:
        if skip_zip(k['start']):
            continue
        if transit_zip(k['start']) and k['mode'] == 'drive_transit':
            continue
        if col.find_one({'_id': k}):
            continue

        doc = {'_id': k, 'weight': home_zips[k['start']]}

        args = {
            'origin': get_zipcode_latlon(k['start']),
            'destination': get_zipcode_latlon(k['end']),
            'arrival_time': utc_timestamp(*k['arrive_by']),
            }
        # Transit-only trip
        if k['mode'] == 'transit':
            args['mode'] = 'transit'
            args['transit_mode'] = ['fewer_transfers']
            commute = call_directions_api(**args)

        # Driving + Transit trip
        elif k['mode'] == 'drive_transit':
            # Get stations
            stations = get_nearby_stations(k['start'])['stations']
            if not stations:
                print('no stations for ' + k['start'])
                continue
            commutes = list()
            for s in stations:
                waypoint = str(s['geo']['lat']) + ',' + str(s['geo']['lng'])
                # Take the train
                args2 = args.copy()
                args2['origin'] = waypoint
                args2['mode'] = 'transit'
                args2['transit_mode'] = ['fewer_transfers']
                leg2 = call_directions_api(**args2)
                if leg2['status'] != 'OK':
                    continue
                time2 = leg2['routes'][0]['legs'][0]['duration']['value']

                # Drive to station
                args1 = args.copy()
                args1['destination'] = waypoint
                args1['mode'] = 'driving'
                leg1 = call_directions_api(**args1)
                if leg1['status'] != 'OK':
                    continue
                time1 = leg1['routes'][0]['legs'][0]['duration']['value']

                # Merge legs
                duration = time1 + time2
                leg1['routes'].append(leg2['routes'][0])
                commutes.append({'time': duration, 'commute': leg1})

            # Choose fastest route
            if not commutes:
                print('no valid driving commutes for ' + k['start'])
                continue
            commutes = sorted(commutes, key=lambda c: c['time'])
            commute = commutes[0]['commute']

        weight = home_zips[k['start']]
        col.insert_one({'_id': k, 'response': commute, 'weight': weight})

def clean_directions():
    # Get MongoDB collections
    raw = mongodb.directions
    clean = mongodb.commutes

    for doc in raw.find():
        if clean.find_one({'_id': doc['_id']}):
            continue
        doc['commute'] = parse_directions(doc.pop('response'))
        clean.insert_one(doc)
