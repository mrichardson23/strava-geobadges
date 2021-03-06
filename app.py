from flask import Flask, render_template, request, url_for, redirect
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
STRAVA_CLIENT_ID = os.environ['STRAVA_CLIENT_ID']
STRAVA_CLIENT_SECRET = os.environ['STRAVA_CLIENT_SECRET']
GOOGLE_MAPS_KEY = os.environ['GOOGLE_MAPS_KEY']
SETUP_PASSWORD = os.environ['SETUP_PASSWORD']


FETCH_COUNT = 200

debug = True
if 'ON_HEROKU' in os.environ:
    debug = False

app = Flask(__name__)
if not debug:
	from flask_sslify import SSLify
	sslify = SSLify(app)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

gmaps = googlemaps.Client(key=GOOGLE_MAPS_KEY)

q = Queue(connection=conn)

from utils import fetchstrava

class Activity(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	strava_user_id = db.Column(db.Integer)
	strava_activity_id = db.Column(db.BigInteger)
	strava_activity_name = db.Column(db.String(140))
	latitude = db.Column(db.Float)
	longitude = db.Column(db.Float)
	country_long = db.Column(db.String(140))
	state_long = db.Column(db.String(140))
	country_short = db.Column(db.String(5))
	state_short = db.Column(db.String(140))
	distance = db.Column(db.Integer)
	start_date = db.Column(db.String(22))
	fetch_time = db.Column(db.Integer)

class User(db.Model):
	strava_user_id = db.Column(db.Integer, primary_key=True)
	strava_access_token = db.Column(db.String(300))
	strava_refresh_token = db.Column(db.String(300))
	strava_access_token_expires_at = db.Column(db.Integer)

class PlaceTotal(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	place_type = db.Column(db.String(7))
	short_name = db.Column(db.String(140))
	total_count = db.Column(db.Integer)
	total_distance = db.Column(db.Integer)

class Place():
	latitude = 0.0
	longitude = 0.0
	country_long = ""
	state_long = ""
	country_short = ""
	state_short = ""

db.create_all()

def fetchactivity(id=0):
	payload = {'access_token': STRAVA_TOKEN}
	a = requests.get('https://www.strava.com/api/v3/athlete/activities?id=' + str(id), params=payload)
	strava_activities = a.json()
	return str(strava_activities)


@app.route('/')
def homepage():
	activities = db.session.query(Activity).filter_by(strava_user_id=3444316)
	places = []
	years = []
	states = []
	countries = []
	for activity in activities:
		x = Place()
		x.latitude = activity.latitude
		x.longitude = activity.longitude
		x.country_long = activity.country_long
		x.country_short = activity.country_short
		x.state_long = activity.state_long
		x.state_short = activity.state_short
		years.append(activity.start_date[:4])
		if activity.country_short == "US":
			states.append(activity.state_short)
		else: #  so that no nulls for state get passed to the template:
			x.state_long = ""
			x.state_short = ""
		countries.append(activity.country_short)
		places.append(x)
	country_count = len(set(countries))
	state_count = len(set(states))

	return render_template('main.html', places = places, years = years, country_count = country_count, state_count = state_count)

@app.route('/state/<place>')
def show_state(place):
	activities = db.session.query(Activity).filter_by(strava_user_id=3444316).filter_by(state_short=place).order_by(Activity.start_date.desc())
	place = activities[0].state_long
	total_distance = 0
	for activity in activities:
		total_distance = total_distance + activity.distance
	return render_template('place.html', activities = activities, place=place, total_distance=total_distance)

@app.route('/country/<place>')
def show_country(place):
	activities = db.session.query(Activity).filter_by(strava_user_id=3444316).filter_by(country_short=place).order_by(Activity.start_date.desc())
	place = activities[0].country_long
	total_distance = 0
	for activity in activities:
		total_distance = total_distance + activity.distance
	return render_template('place.html', activities = activities, place=place, total_distance=total_distance)

@app.route('/setup', methods=['GET', 'POST'])
def update():
	messages = []
	if request.method == 'GET':
		if request.args.get('code') is not None:
			payload = {
				'client_id': '24763',
    			'client_secret': STRAVA_CLIENT_SECRET,
    			'code': request.args.get('code'),
    			'grant_type': 'authorization_code'
			}
			r = requests.post("https://www.strava.com/oauth/token", params=payload)
			jsonResponse = r.json()
			messages.append("Strava access token: " + jsonResponse['access_token'])
			messages.append("token expires at: " + str(jsonResponse['expires_at']))
			athlete_id = int(jsonResponse['athlete']['id'])
			if db.session.query(User).filter_by(strava_user_id=athlete_id).count() == 0:
				user = User()
				user.strava_user_id = athlete_id
				user.strava_access_token = jsonResponse['access_token']
				user.strava_refresh_token = jsonResponse['refresh_token']
				user.strava_access_token_expires_at = jsonResponse['expires_at']
				db.session.add(user)
				messages.append('Added Strava user ' + str(athlete_id) + '.')
			else:
				user = db.session.query(User).filter_by(strava_user_id=athlete_id).one()
				user.strava_access_token = jsonResponse['access_token']
				user.strava_refresh_token = jsonResponse['refresh_token']
				user.strava_access_token_expires_at = jsonResponse['expires_at']
				messages.append('Refreshed token for Strava user ' + str(athlete_id) + '.')
			db.session.commit()
			return render_template('setup.html', messages=messages)
		else:
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
				if action == "view_activity":
					messages.append(fetchactivity(request.form['strava_id']))
				if action == "authorize":
					return redirect("https://www.strava.com/oauth/authorize?client_id=" + STRAVA_CLIENT_ID + "&redirect_uri=https://run.mattrichardson.com/setup&response_type=code&scope=activity:read_all")
		else:
			messages.append("Wrong password!")
		return render_template('setup.html', messages=messages)

@app.route('/year/<year>')
def show_year(year):
	activities = db.session.query(Activity).filter_by(strava_user_id=3444316).filter(Activity.start_date.like(year+'%')).order_by(Activity.start_date.desc())
	total_distance = 0
	places = []
	states = []
	countries = []
	for activity in activities:
		x = Place()
		x.latitude = activity.latitude
		x.longitude = activity.longitude
		x.country_long = activity.country_long
		x.country_short = activity.country_short
		x.state_long = activity.state_long
		x.state_short = activity.state_short
		places.append(x)
		if activity.country_short == "US":
			states.append(activity.state_short)
		else: #  so that no nulls for state get passed to the template:
			x.state_long = ""
			x.state_short = ""
		countries.append(activity.country_short)
		total_distance = total_distance + activity.distance
	country_count = len(set(countries))
	state_count = len(set(states))
	activity_count = activities.count()

	return render_template('year.html', activities = activities, year=year, total_distance=total_distance, places=places, state_count=state_count, country_count=country_count, activity_count=activity_count)


if __name__ == '__main__':
	if debug:
		app.run(debug=True, use_reloader=True)
	else:
		app.run()
