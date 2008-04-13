import os
import time
import select
import traceback

from datetime import datetime
from threading import Thread

from ZDStack.Alarm import Alarm
from ZDStack.LogEvent import LogEvent

# def L(x):
#     fobj = open('/root/ZDStack/bin/out.log', 'a')
#     fobj.write(x + '\n')
#     fobj.flush()
#     fobj.close()

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
        Thread(target=self.log).start()

    def __str__(self):
        return "<%s LogFile %s>" % (self.log_type.capitalize(),
                                    os.path.basename(self.file_path))

    def __repr__(self):
        return "LogFile(%s, %s, %s)" % (self.file_path, self.log_type,
                                        repr(self.parser))

    def set_filepath(self, filepath):
        self.filepath = filepath
        self.new_filepath = True

    def log(self):
        unprocessed_data = ''
        while 1:
            if self.new_filepath:
                self.zserv.log("Received new filepath [%s]" % (self.new_filepath))
                self.new_filepath = False
                if self.fobj:
                    self.fobj.close()
                self.fobj = None
            while not self.fobj:
                self.zserv.log("No fileobject: [%s]" % (self.filepath))
                time.sleep(.3) # wait for the file to appear if it doesn't exist
                if os.path.isfile(self.filepath):
                    self.zserv.log("Found a fileobject [%s]" % (self.filepath))
                    self.fobj = open(self.filepath)
            events = []
            rs, ws, xs = select.select([self.fobj], [], [])
            for r in rs:
                unprocessed_data += self.fobj.read()
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
                if event.type.startswith('rcon'):
                    # self.zserv.log("Got RCON event: [%s]" % (event.type))
                    pass
                else:
                    self.zserv.log("Sending event [%s: %s]" % (event.type, str(event.data)))
                for listener in self.listeners:
                    listener.send_event(event)
            time.sleep(.05) # higher resolutions burn up CPU unnecessarily

