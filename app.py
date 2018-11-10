from flask import Flask, render_template, request, url_for
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
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

gmaps = googlemaps.Client(key=GOOGLE_MAPS_KEY)

q = Queue(connection=conn)

from utils import fetchstrava

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
	distance = db.Column(db.Integer)
	start_date = db.Column(db.String(22))
	fetch_time = db.Column(db.Integer)

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

@app.route('/')
def homepage():
	activities = db.session.query(Activity).filter_by(strava_user_id=3444316)
	places = []
	years = []
	for activity in activities:
		x = Place()
		x.latitude = activity.latitude
		x.longitude = activity.longitude
		x.country_long = activity.country_long
		x.country_short = activity.country_short
		x.state_long = activity.state_long
		x.state_short = activity.state_short
		years.append(activity.start_date[:4])
		places.append(x)

	return render_template('main.html', places = places, years = years)

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

@app.route('/year/<year>')
def show_year(year):
	activities = db.session.query(Activity).filter_by(strava_user_id=3444316).filter(Activity.start_date.like(year+'%')).order_by(Activity.start_date.desc())
	total_distance = 0
	places = []
	for activity in activities:
		x = Place()
		x.latitude = activity.latitude
		x.longitude = activity.longitude
		x.country_long = activity.country_long
		x.country_short = activity.country_short
		x.state_long = activity.state_long
		x.state_short = activity.state_short
		places.append(x)
		total_distance = total_distance + activity.distance

	return render_template('year.html', activities = activities, year=year, total_distance=total_distance, places=places)

if __name__ == '__main__':
	app.run(debug=True, use_reloader=True)
