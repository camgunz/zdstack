class LogEvent:

    def __init__(self, event_dt, event_type, event_data):
        self.dt = event_dt
        self.type = event_type
        self.data = event_data

    def __str__(self):
        return "<%s event at %s>" % (self.type, self.dt)

    def __repr__(self):
        return "LogEvent(%s, %s, %s)" % (self.dt, self.type, self.data)

    def __eq__(self, x):
        try:
            return self.dt == x.dt and self.type == x.type \
               and self.data == x.data
        except AttributeError:
            return False

    def __lt__(self, x):
        try:
            return self.type == x.type and self.dt < x.dt
        except AttributeError:
            return False

    def __gt__(self, x):
        try:
            return self.type == x.type and self.dt > x.dt
        except AttributeError:
            return False

