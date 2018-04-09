from flask import Flask, render_template
from datetime import datetime
import os
import psycopg2
import requests

DATABASE_URL = os.environ['DATABASE_URL']
STRAVA_TOKEN = os.environ['STRAVA_TOKEN']

conn = psycopg2.connect(DATABASE_URL)

app = Flask(__name__)

@app.route('/')
def homepage():
	payload = {'access_token': STRAVA_TOKEN}
	a = requests.get('https://www.strava.com/api/v3/athlete/activities?per_page=200', params=payload)
	return render_template('main.html', activities = a.json())
if __name__ == '__main__':
	app.run(debug=True, use_reloader=True)
