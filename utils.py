import os
import requests
import googlemaps
import time
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

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
	fetch_time = db.Column(db.Integer)


class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	strava_user_id = db.Column(db.Integer)
	most_recent_download = db.Column(db.BigInteger)

gmaps = googlemaps.Client(key=GOOGLE_MAPS_KEY)

def fetchstrava(after_time=0):
	payload = {'access_token': STRAVA_TOKEN}
	count = 0
	done = False
	page = 1
	while done is False:
		a = requests.get('https://www.strava.com/api/v3/athlete/activities?after=' + str(after_time) + '&per_page=' + str(FETCH_COUNT) + '&page=' + str(page), params=payload)
		strava_activities = a.json()
		if len(strava_activities) < FETCH_COUNT:
			done = True
		else:
			page = page + 1
		for strava_activity in strava_activities:
			if strava_activity['start_latitude'] is not None:
				if strava_activity['type'] == 'Run':
					x = Activity()
					x.strava_user_id = strava_activity['athlete']['id']
					x.strava_activity_id = strava_activity['id']
					x.strava_activity_name = strava_activity['name']
					x.latitude = strava_activity['start_latitude']
					x.longitude = strava_activity['start_longitude']
					gmaps_output = gmaps.reverse_geocode((strava_activity['start_latitude'], strava_activity['start_longitude']))
					address_components = gmaps_output[0]['address_components']
					for address_component in address_components:
						if address_component['types'][0] == 'administrative_area_level_1':
							x.state_long = address_component['long_name']
							x.state_short = address_component['short_name']
						if address_component['types'][0] == 'country':
							x.country_long = address_component['long_name']
							x.country_short = address_component['short_name']
					x.fetch_time = int(time.time())
					db.session.add(x)
					count = count + 1
	db.session.commit()
	return count

def getlocations():
	activities = db.session.query(Activity).filter_by(strava_user_id=3444316).filter_by(country_long=None)
	count = 0
	for activity in activities:
		gmaps_output = gmaps.reverse_geocode((activity.latitude, activity.longitude))
		row = db.session.query(Activity).filter(Activity.id == activity.id).first()
		address_components = gmaps_output[0]['address_components']
		for address_component in address_components:
			if address_component['types'][0] == 'administrative_area_level_1':
				row.state_long = address_component['long_name']
				row.state_short = address_component['short_name']
			if address_component['types'][0] == 'country':
				row.country_long = address_component['long_name']
				row.country_short = address_component['short_name']
		db.session.commit()
		count = count + 1
	return count
