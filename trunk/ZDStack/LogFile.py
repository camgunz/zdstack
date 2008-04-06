import os
import time
from threading import Thread

from ZDStack.Alarm import Alarm
from ZDStack.LogEvent import LogEvent

class LogFile:

    def __init__(self, file_path, log_type, parser, listeners=[]):
        self.file_object = None
        self.new_filepath = False
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

    def set_filepath(self, filepath):
        self.filepath = filepath
        self.new_filepath = True

    def get_events(self):
        unprocessed_data = ''
        while 1:
            if self.new_filepath:
                self.new_filepath = False
                self.fobj.close()
                self.fobj = None
            while not self.fobj:
                time.sleep(1) # wait for the file to appear if it doesn't exist
                if os.path.isfile(self.filepath):
                    self.fobj = open(self.filepath)
            events = []
            unprocessed_data += self.fobj.read()
            try:
                events, unprocessed_data = self.parse(unprocessed_data)
            except Exception, e:
                events = [LogEvent(datetime.now(), 'error', str(e))]
            for event in event:
                yield event

