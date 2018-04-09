from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import os
import sys
import requests
import googlemaps

DATABASE_URL = os.environ['DATABASE_URL']
STRAVA_TOKEN = os.environ['STRAVA_TOKEN']
GOOGLE_MAPS_KEY = os.environ['GOOGLE_MAPS_KEY']
FETCH_COUNT = 200

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

db = SQLAlchemy(app)
migrate = Migrate(app, db)

gmaps = googlemaps.Client(key=GOOGLE_MAPS_KEY)

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

@app.route('/fetch-strava')
def fetchstrava():
	payload = {'access_token': STRAVA_TOKEN}
	count = 0
	done = False
	page = 1
	while done is False:
		a = requests.get('https://www.strava.com/api/v3/athlete/activities?per_page=' + str(FETCH_COUNT) + '&page=' + str(page), params=payload)
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
					db.session.add(x)
					count = count + 1
	db.session.commit()
	output = "Saved " + str(count) + " records from Strava. Activity type: " + strava_activities[0]['type']
	return render_template('debug.html', output=output)

@app.route('/getlocations')
def getlocations():
	activities = db.session.query(Activity).filter_by(strava_user_id=3444316)
	count = 0
	for activity in activities:
		gmaps_output = gmaps.reverse_geocode((activity.latitude, activity.longitude))
		row = db.session.query(Activity).filter(Activity.strava_activity_id == activity.strava_activity_id).first()
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
	output = "Updated records: " + str(count)
	return render_template('debug.html', output = output)

if __name__ == '__main__':
	app.run(debug=True, use_reloader=True)
