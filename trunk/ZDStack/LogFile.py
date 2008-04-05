import os
import time
from threading import Thread

from ZDStack.LogEvent import LogEvent

class LogFile:

    def __init__(self, file_path, log_type, parser, listeners=[]):
        if not os.path.isfile(file_path):
            fd = os.open(os.O_CREAT, file_path)
            os.close(fd)
        ###
        # Here, we want to automatically roll the log over if it exists.  This
        # entails adding a number extension to the log and gzipping it.
        ###
        self.file_path = file_path
        self.file_object = open(self.file_path)
        self.log_type = log_type
        self.parser = parser
        self.parse = self.parser # tricky!
        self.listeners = listeners
        self.events = self.get_events()
        Thread(self.log).start()

    def __str__(self):
        return "<%s LogFile %s>" % (self.log_type.capitalize(),
                                    os.path.basename(self.file_path))

    def __repr__(self):
        return "LogFile(%s, %s, %s)" % (self.file_path, self.log_type,
                                        repr(self.parser))

    def log(self):
        while 1:
            event = self.events.next()
            for listener in self.listeners:
                Thread(listener.handle_event, args=[event]).start()
            time.sleep(.01) # higher resolutions burn up CPU unnecessarily

    def get_events(self):
        unprocessed_data = ''
        while 1:
            events = []
            unprocessed_data += self.fobj.read()
            try:
                events, unprocessed_data = self.parse(unprocessed_data)
            except Exception, e:
                events = [LogEvent(datetime.now(), 'error', str(e))]
            for event in event:
                yield event

