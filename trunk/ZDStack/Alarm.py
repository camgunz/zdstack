from threading import _Timer
from datetime import datetime, timedelta

def timedelta_in_seconds(x):
    return (x.days * 86400) + x.seconds

class Alarm(_Timer):

    def __init__(self, alarm_time, func, args=[], kwargs={}):
        now = datetime.now()
        seconds = timedelta_in_seconds(alarm_time - now)
        if seconds <= 0:
            es = "Must set Alarm for a time in the future: [%s] [%s]"
            raise ValueError(es % (now, alarm_time))
        _Timer.__init__(self, seconds, func, args, kwargs)

