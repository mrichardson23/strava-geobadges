from apscheduler.schedulers.blocking import BlockingScheduler
from rq import Queue
from worker import conn
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app import db

q = Queue(connection=conn)
sched = BlockingScheduler()

from app import Activity

@sched.scheduled_job('interval', minutes=2)
def timed_job():
	last_record = db.session.query(Activity).order_by(Activity.fetch_time.desc()).first()
	if last_record:
		after_time = last_record.fetch_time
	else:
		after_time = 0
	print("Checking Strava for activities since: " + str(after_time))
	strava_result = q.enqueue(fetchstrava, after_time=after_time)
sched.start()