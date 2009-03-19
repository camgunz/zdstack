from __future__ import with_statement

import os
import time
import logging
import traceback

from datetime import datetime
from threading import Lock, Event

from ZDStack import TICK
from ZDStack.LogEvent import LogEvent

class LogFile(object):

    """LogFile represents a zserv log file."""

    def __init__(self, parser, zserv, listeners=[]):
        """Initializes a LogFile instance.

        parser:    a LogParser instance
        zserv:     a ZServ instance
        listeners: a list of LogListener instances to send events to

        """
        self.closed = False
        self.encoding = None
        self.errors = None
        self.newlines = None
        self.softspace = 0
        self.parse = parser # tricky!
        self.zserv = zserv
        self.listeners = listeners
        self.unprocessed_data = ''
        self.command_lock = Lock()
        self.event_to_watch_for = None
        self.response_events = []
        self.response_finished = Event()

    def __str__(self):
        return "<LogFile for %s>" % (self.zserv.name)

    def __repr__(self):
        return "LogFile(%r, %r, %r)" % (self.parse, self.zserv, self.listeners)

    def close(self):
        self.closed = True

    def flush(self):
        pass

    def isatty(self):
        return False

    def next(self):
        ###
        # Normally file objects are their own iterators, returning lines of
        # their contents.  This file object has no contents, so this
        # automatically raises StopIteration
        ###
        raise StopIteration

    def read(self, size=None):
        ###
        # Normally file objects have contents, but this file object doesn't.
        ###
        return ''

    def readline(self, size=None):
        ###
        # Normally file objects have contents, but this file doesn't.
        ###
        return ''

    def readlines(self, sizehint=None):
        ###
        # Normally file objects have contents, but this file doesn't.
        ###
        return []

    def xreadlines(self):
        ###
        # Normally file objects have contents, but this file doesn't.
        ###
        raise StopIteration

    def seek(self, offset, whence=None):
        pass

    def tell(self):
        return 0

    def truncate(self, size=None):
        pass

    def write(self, s):
        if not self.zserv.events_enabled:
            return
        self.unprocessed_data += s
        if self.unprocessed_data:
            self.process_data()

    def writelines(self, seq):
        self.write(''.join(seq))

    def start_listeners(self):
        """Starts all listeners in self.listeners."""
        for x in self.listeners:
            logging.debug("Starting %s" % (listener.name))
            x.start()

    def stop_listeners(self):
        """Stops all listeners in self.listeners."""
        for x in self.listeners:
            logging.debug("Stopping %s" % (listener.name))
            x.stop() # should kill all listener threads

    def watch_for_response(self, response_event_type):
        """Starts watching for a certain event type.

        response_event_type: a string representing the type of event
                             to watch for.

        This method starts watching for a certain event type, and
        stores matching events in self.response_events.  A Logfile
        stops watching for response events only when it finds a
        matching event (or events) and then finds one that doesn't.

        """
        # logging.debug('')
        if not self.zserv.events_enabled:
            return
        with self.command_lock:
            while self.event_to_watch_for is not None:
                ###
                # Wait for any previous response watching to finish
                ###
                time.sleep(TICK)
                self.event_to_watch_for = response_event_type
                self.response_events = []
            ###
            # Un-set the "end of response" event
            ###
            self.response_finished.clear()

    def get_response(self):
        """Returns the list of saved response events."""
        if not self.zserv.events_enabled:
            return []
        # logging.debug('')
        output = []
        ###
        # Wait for the end of a response (response_finished will be "set"),
        # but only wait 1 second... which is actually a long time.
        ###
        self.response_finished.wait(1)
        ###
        # Reset the "end of response" event
        ###
        self.response_finished.clear()
        ###
        # Add all received events to an output list as dicts
        ###
        for event in self.response_events:
            d = {'type': event.type}
            d.update(event.data)
            output.append(d)
        self.response_events = []
        return output

    def process_data(self):
        """Processes the unprocessed data buffer.

        Unprocessed data is parsed into events, which are placed in
        the event queue of every listener in self.listeners.

        """
        events = []
        try:
            events, self.unprocessed_data = self.parse(self.unprocessed_data)
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
                    logging.info(s)
                    continue
                message = c.replace(player.name, '', 1)[3:]
                d = {'message': message, 'messenger': player}
                event = LogEvent(event.dt, 'message', d, event.line)
            if self.event_to_watch_for:
                if event.type == self.event_to_watch_for:
                    self.response_events.append(event)
                elif self.response_events:
                    ###
                    # Received an event that was not a response to the command,
                    # so notify watch_for_response that we're done and clear
                    # "event to watch for".
                    ###
                    self.response_finished.set()
                    self.event_to_watch_for = None
            for listener in self.listeners:
                if event.type != 'junk':
                    es = 'LogFile for %s putting Event %s in Listener %s'
                    t = (self.zserv.name, event.type, listener.name)
                    logging.debug(es % t)
                    ###
                    # Don't process junk events, waste of cycles
                    ###
                    listener.events.put_nowait(event)

