import os
import time
import select
import logging
import traceback

from datetime import datetime
from threading import Lock, Event

from ZDStack import log
from ZDStack.Utils import start_thread
from ZDStack.LogEvent import LogEvent

class LogFile:

    def __init__(self, log_type, parser, zserv, listeners=[]):
        self.fobj = None
        self.filepath = None
        self.log_type = log_type
        self.parse = parser # tricky!
        self.zserv = zserv
        self.listeners = listeners
        self.keep_logging = False
        self.logging_thread = None
        self.change_file_lock = Lock()
        self.command_lock = Lock()
        self.event_to_watch_for = None
        self.response_events = []
        self.response_finished = Event()

    def __str__(self):
        return "<%s LogFile %s>" % (self.log_type.capitalize(),
                                    os.path.basename(self.filepath))

    def __repr__(self):
        return "LogFile(%s, %s, %r)" % (self.filepath, self.log_type,
                                        self.parse)

    def start(self):
        self.keep_logging = True
        self.logging_thread = \
            start_thread(self.log, '%s logging thread' % (self.filepath))

    def stop(self):
        self.keep_logging = False
        # self.logging_thread.join()

    def set_filepath(self, filepath, seek_to_end=False):
        # log("Received new filepath [%s]" % (self.filepath))
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

    def watch_for_response(self, response_event_type):
        logging.getLogger('').debug('')
        self.command_lock.acquire()
        try:
            while self.event_to_watch_for is not None:
                time.sleep(.05)
            self.event_to_watch_for = response_event_type
            self.response_events = []
        finally:
            self.command_lock.release()
        self.response_finished.clear()

    def get_response(self):
        logging.getLogger('').debug('')
        output = []
        self.response_finished.wait(2)
        self.response_finished.clear()
        for event in self.response_events:
            d = {'type': event.type}
            d.update(event.data)
            output.append(d)
        self.event_to_watch_for = None
        self.response_events = []
        return output

    def log(self):
        unprocessed_data = ''
        while self.keep_logging:
            ###
            # We put sleep up at the top to ensure it gets done.  Otherwise
            # CPU usage can go through the roof
            ###
            time.sleep(.05) # higher resolutions burn up CPU unnecessarily
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
                    if event.type == 'message':
                        ppn = event.data['possible_player_names']
                        c = event.data['contents'] 
                        player = self.zserv.distill_player(ppn)
                        if not player:
                            s = "Received a message from a non-existent player"
                            logging.getLogger('').info(s)
                            continue
                        message = c.replace(player.name, '', 1)[3:]
                        d = {'message': message, 'messenger': player}
                        event = LogEvent(event.dt, 'message', d)
                    if self.event_to_watch_for:
                        if event.type == self.event_to_watch_for:
                            self.response_events.append(event)
                        elif self.response_events:
                            self.response_finished.set()
                            # notify watch_for_response that we're done
                    for listener in self.listeners:
                        if event.type != 'junk':
                            logging.getLogger('').debug(es % (event.type))
                        s = "Putting %s in %s"
                        logging.getLogger('').debug(s % (event.type, listener.name))
                        listener.events.put_nowait(event)
            elif self.filepath and os.path.isfile(self.filepath):
                self.change_file_lock.acquire()
                try:
                    self.fobj = open(self.filepath)
                finally:
                    self.change_file_lock.release()
            else:
                logging.getLogger('').debug("%s: No fobj" % (self.filepath))

