from threading import Event

class LogEvent(object):

    """LogEvent represents an event occurring in a log file.
    
    .. attribute:: dt
        A datetime representing the time at which the event occurred.
    .. attribute:: type
        A string representing the type of the event.
    .. attribute:: data
        A dict containing event-specific data.
    .. attribute:: category
        A string representing the category of the event.
    .. attribute:: handled
        An Event instance that is set() when the EventHandler has
        handled the event.
    
    """

    def __init__(self, event_dt, event_type, event_data, event_category,
                       line=''):
        """Initializes a LogEvent instance.


        """
        self.dt = event_dt
        self.type = event_type
        self.data = event_data
        self.category = event_category
        self.line = line
        self.handled = Event()

    def __str__(self):
        return "<Event %s at %s>" % (self.type, self.dt)

    def __repr__(self):
        return "LogEvent(%s, %s, %s, %s)" % (self.dt, self.type, self.data,
                                             self.category)

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

