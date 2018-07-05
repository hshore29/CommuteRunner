import os
import sqlite3
import polyline
import mongo_conn as M
from flask import Flask, render_template, jsonify
app = Flask(__name__)

unpolyline = lambda p: list(map(list, map(reversed, polyline.decode(p))))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data/<element>')
def get_data(element):
    db = sqlite3.connect('Census Data/census.db').cursor()
    db.execute('SELECT ZCTA5, %s FROM zip_data' % element)
    data = {z[0]: z[1] for z in db.fetchall()}
    return jsonify(data)

@app.route('/commutes/times/<work_zip>')
def get_commute_times(work_zip):
    docs = list(M.aggregate_commute_times(work_zip))
    zips = {z['zip']: z['duration'] for z in docs}
    total = sum([z['weight']*z['duration'] for z in docs]) /\
            sum([z['duration'] for z in docs])
    return jsonify({'zips': zips, 'total': total})

@app.route('/commutes/lines/<work_zip>')
def get_commute_lines(work_zip):
    docs = list(M.aggregate_commute_steps(work_zip))
    for d in docs:
        polyline = d.pop('polyline')
        startend = d.pop('startend')
        if d['mode'] in ('TRANSIT', 'DRIVING_ONLY', 'WALKING_ONLY'):
            coords = unpolyline(polyline)
        else:
            coords = startend
        d['geo'] = {'type': 'LineString', 'coordinates': coords}

    return jsonify(docs)
