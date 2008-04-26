import os
import time
import select
import traceback

from datetime import datetime
from threading import Lock

from ZDStack import start_thread, log, debug
from ZDStack.LogEvent import LogEvent

class LogFile:

    def __init__(self, log_type, parser, zserv, listeners=[]):
        self.fobj = None
        self.filepath = None
        self.log_type = log_type
        self.parser = parser
        self.zserv = zserv
        self.parse = self.parser # tricky!
        self.listeners = listeners
        self.keep_logging = False
        self.logging_thread = None
        self.change_file_lock = Lock()

    def start(self):
        self.keep_logging = True
        self.logging_thread = \
            start_thread(self.log, '%s logging thread' % (self.filepath))

    def stop(self):
        self.keep_logging = False
        # self.logging_thread.join()

    def __str__(self):
        return "<%s LogFile %s>" % (self.log_type.capitalize(),
                                    os.path.basename(self.filepath))

    def __repr__(self):
        return "LogFile(%s, %s, %r)" % (self.filepath, self.log_type,
                                        self.parser)

    def set_filepath(self, filepath, seek_to_end=False):
        log("Received new filepath [%s]" % (self.filepath))
        self.change_file_lock.acquire()
        try:
            self.filepath = filepath
            if self.fobj:
                self.fobj.close()
                self.fobj = None
            if os.path.isfile(self.filepath):
                self.fobj = open(self.filepath)
                if seek_to_end:
                    self.fobj.seek(0, os.SEEK_END)
        finally:
            self.change_file_lock.release()

    def log(self):
        unprocessed_data = ''
        while self.keep_logging:
            events = []
            if self.fobj:
                self.change_file_lock.acquire()
                try:
                    try:
                        rs, ws, xs = select.select([self.fobj], [], [])
                    except: # can be raised during interpreter shutdown
                        continue
                    for r in rs:
                        unprocessed_data += r.read()
                finally:
                    self.change_file_lock.release()
                try:
                    events, unprocessed_data = \
                                        self.parse(unprocessed_data)
                except Exception, e:
                    # raise # for debugging
                    tb = traceback.format_exc()
                    ed = {'error': e, 'traceback': tb}
                    events = [LogEvent(datetime.now(), 'error', ed)]
                for event in events:
                    es = "%s Sending event [%%s]" % (self.filepath)
                    for listener in self.listeners:
                        if event.type != 'junk':
                            debug(es % (event.type))
                        listener.events.put_nowait(event)
            elif self.filepath and os.path.isfile(self.filepath):
                self.change_file_lock.acquire()
                try:
                    self.fobj = open(self.filepath)
                finally:
                    self.change_file_lock.release()
            else:
                debug("%s: No fobj" % (self.filepath))
            time.sleep(.05) # higher resolutions burn up CPU unnecessarily

