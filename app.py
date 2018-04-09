from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import os
import sys
import requests
import googlemaps
from rq import Queue
from worker import conn

DATABASE_URL = os.environ['DATABASE_URL']
STRAVA_TOKEN = os.environ['STRAVA_TOKEN']
GOOGLE_MAPS_KEY = os.environ['GOOGLE_MAPS_KEY']
SETUP_PASSWORD = os.environ['SETUP_PASSWORD']
FETCH_COUNT = 200

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

db = SQLAlchemy(app)
migrate = Migrate(app, db)

gmaps = googlemaps.Client(key=GOOGLE_MAPS_KEY)

q = Queue(connection=conn)
from utils import fetchstrava, getlocations

class Activity(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	strava_user_id = db.Column(db.Integer)
	strava_activity_id = db.Column(db.Integer)
	strava_activity_name = db.Column(db.String(140))
	latitude = db.Column(db.Float)
	longitude = db.Column(db.Float)
	country_long = db.Column(db.String(140))
	state_long = db.Column(db.String(140))
	country_short = db.Column(db.String(5))
	state_short = db.Column(db.String(140))

class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	strava_user_id = db.Column(db.Integer)
	most_recent_download = db.Column(db.BigInteger)

db.create_all()

@app.route('/')
def homepage():
	activities = db.session.query(Activity).filter_by(strava_user_id=3444316)
	states = []
	countries = []
	for activity in activities:
		countries.append(activity.country_long)
		if activity.country_short == "US":
			states.append(activity.state_long)
	states = set(states)
	countries = set(countries)
	return render_template('main.html', states=states, countries=countries)

@app.route('/setup', methods=['GET', 'POST'])
def update():
	messages = []
	if request.method == 'GET':
		messages.append("Make changes and enter password to submit.")
		return render_template('setup.html', messages=messages)
	if request.method == 'POST':
		if request.form['psw'] == SETUP_PASSWORD:
			for action in request.form.getlist('action'):
				if action == "strava":
					strava_result = q.enqueue(fetchstrava)
					messages.append("Fetching activities from Strava in the background.")
				if action == "geocode":
					geocode_result = q.enqueue(getlocations)
					messages.append("Geocoding activities in the background.")
		else:
			messages.append("Wrong password!")
		return render_template('setup.html', messages=messages)

if __name__ == '__main__':
	app.run(debug=True, use_reloader=True)
