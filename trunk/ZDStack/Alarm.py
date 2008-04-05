from threading import Timer
from datetime import datetime, timedelta

def timedelta_in_seconds(x):
    return (x.days * 86400) + x.seconds

class Alarm(Timer):

    def __init__(self, alarm_time, func, args=[], kwargs={}):
        now = datetime.now()
        seconds = timedelta_in_seconds(alarm_time - now)
        if seconds <= 0:
            raise ValueError("Must set Alarm for a time in the future")
        Timer(self, seconds, func, args, kwargs).
