from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import os
import requests

DATABASE_URL = os.environ['DATABASE_URL']
STRAVA_TOKEN = os.environ['STRAVA_TOKEN']

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Activity(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	strava_user_id = db.Column(db.Integer)
	strava_activity_id = db.Column(db.Integer)
	strava_activity_name = db.Column(db.String(140))
	latitude = db.Column(db.Float)
	longitude = db.Column(db.Float)

db.create_all()

@app.route('/')
def homepage():
	activities = db.session.query(Activity).filter_by(strava_user_id=3444316)
	return render_template('main.html', activities=activities)

@app.route('/refresh')
def refresh():
	payload = {'access_token': STRAVA_TOKEN}
	a = requests.get('https://www.strava.com/api/v3/athlete/activities?per_page=200', params=payload)
	strava_activities = a.json()
	for strava_activity in strava_activities:
		x = Activity()
		x.strava_user_id = 3444316
		x.strava_activity_id = strava_activity['id']
		x.strava_activity_name = strava_activity['name']
		x.latitude = strava_activity['start_latitude']
		x.longitude = strava_activity['start_longitude']
		db.session.add(x)
	db.session.commit()
	return render_template('main.html', activities = a.json(), message="Records added.")

if __name__ == '__main__':
	app.run(debug=True, use_reloader=True)
