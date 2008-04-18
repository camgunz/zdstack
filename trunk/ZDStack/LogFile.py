import os
import time
import select
import traceback

from datetime import datetime

from ZDStack import start_thread
from ZDStack.LogEvent import LogEvent

class LogFile:

    def __init__(self, log_type, parser, zserv, listeners=[]):
        self.fobj = None
        self.filepath = None
        self.new_filepath = False
        self.log_type = log_type
        self.parser = parser
        self.zserv = zserv
        self.parse = self.parser # tricky!
        self.listeners = listeners
        self.keep_logging = False
        self.logging_thread = None

    def start(self):
        self.keep_logging = True
        self.logging_thread = start_thread(self.log)

    def stop(self):
        self.keep_logging = False
        # self.logging_thread.join()

    def __str__(self):
        return "<%s LogFile %s>" % (self.log_type.capitalize(),
                                    os.path.basename(self.filepath))

    def __repr__(self):
        return "LogFile(%s, %s, %r)" % (self.filepath, self.log_type,
                                        self.parser)

    def set_filepath(self, filepath):
        self.filepath = filepath
        self.new_filepath = True

    def log(self):
        unprocessed_data = ''
        while self.keep_logging:
            if self.new_filepath:
                self.zserv.log("Received new filepath [%s]" % (self.filepath))
                self.new_filepath = False
                if self.fobj:
                    self.fobj.close()
                self.fobj = None
            while not self.fobj:
                # self.zserv.log("No fileobject: [%s]" % (self.filepath))
                time.sleep(.3) # wait for the file to appear if it doesn't exist
                if os.path.isfile(self.filepath):
                    self.new_filepath = False
                    # self.zserv.log("Found a fileobject [%s]" % (self.filepath))
                    self.fobj = open(self.filepath)
                    self.fobj.seek(0, os.SEEK_END)
            events = []
            rs, ws, xs = select.select([self.fobj], [], [])
            for r in rs:
                unprocessed_data += r.read()
                try:
                    events, unprocessed_data = self.parse(unprocessed_data)
                except Exception, e:
                    self.zserv.log("events: %s" % (events))
                    self.zserv.log("unprocessed_data: %s" % (unprocessed_data))
                    raise # for debugging
                    tb = traceback.format_exc()
                    ed = {'error': e, 'traceback': tb}
                    events = [LogEvent(datetime.now(), 'error', ed)]
            for event in events:
                # es = "Sending event [%s]"
                for listener in self.listeners:
                    # if event.type != 'junk':
                    #     self.zserv.log(es % (event.type))
                    listener.send_event(event)
            time.sleep(.05) # higher resolutions burn up CPU unnecessarily

