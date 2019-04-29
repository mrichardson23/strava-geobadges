from apscheduler.schedulers.blocking import BlockingScheduler
from rq import Queue
from worker import conn
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app import db
import utils
import time

q = Queue(connection=conn)
sched = BlockingScheduler()

from app import Activity

@sched.scheduled_job('interval', minutes=60)
def activity_checker():
	last_record = db.session.query(Activity).order_by(Activity.fetch_time.desc()).first()
	if last_record:
		after_time = last_record.fetch_time
	else:
		after_time = 0
	print("Checking Strava for activities since: " + str(after_time))
	strava_result = q.enqueue(utils.fetchstrava, after_time=after_time)


@sched.scheduled_job('interval', minutes=60)
def activity_name_updater():
	print("Updating activity names...")
	after_time = int(time.time()) - 86400
	strava_result = q.enqueue(utils.activityNameUpdate, after_time=after_time)

sched.start()