class LogEvent:

    """LogEvent represents an event occurring in a log file."""

    def __init__(self, event_dt, event_type, event_data, event_category,
                       line=''):
        """Initializes a LogEvent instance.

        event_dt:       a datetime representing the time at which the
                        event occurred.
        event_type:     a string representing the type of the event.
        event_data:     a dict of event data.
        event_category: the category this event belongs to.
        line:           optional, a string representing the line this
                        event was created to represent.

        """
        self.dt = event_dt
        self.type = event_type
        self.data = event_data
        self.category = event_category
        self.line = line

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

