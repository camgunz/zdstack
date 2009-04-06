from __future__ import with_statement

import os
import time
import logging
import traceback

from datetime import datetime
from threading import Lock, Event

from ZDStack import ZDSThreadPool

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
        self.errors = None
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

    def write(self, s):
        if not self.zserv.events_enabled:
            return
        # logging.debug("Adding %s to unprocessed data" % (s))
        self.unprocessed_data += s
        if self.unprocessed_data:
            self.process_data()

    def start_listeners(self):
        """Starts all listeners in self.listeners."""
        for x in self.listeners:
            logging.debug("Starting %s" % (x.name))
            x.start()

    def stop_listeners(self):
        """Stops all listeners in self.listeners."""
        for x in self.listeners:
            logging.debug("Stopping %s" % (x.name))
            ###
            # x.stop() # should kill all listener threads
            ###
            x.keep_listening = False
            if x.command_listener_thread:
                logging.debug("Joining GLL Command Listener Thread")
                ZDSThreadPool.join(x.command_listener_thread)
            if x.generic_listener_thread:
                logging.debug("Joining GLL Generic Listener Thread")
                ZDSThreadPool.join(x.generic_listener_thread)
        logging.debug("Stopped all listeners")

    def set_response_type(self, response_event_type):
        """Sets the type of event to store as a command response.

        response_event_type: a string representing the type of event
                             to watch for.

        This method causes the LogFile to save events of the given type
        to self.response_events.  A Logfile stops watching for response
        response events only when it finds a matching event (or events)
        and then finds one that doesn't.

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
            self.response_events = []
            self.event_to_watch_for = response_event_type
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
        # Clear all response stuff.
        ###
        for event in self.response_events:
            d = {'type': event.type}
            d.update(event.data)
            output.append(d)
        self.event_to_watch_for = None
        self.response_events = []
        ###
        # Reset the "end of response" event
        ###
        self.response_finished.clear()
        ###
        # Add all received events to an output list as dicts
        ###
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
            events = [LogEvent(datetime.now(), 'error', ed, 'error')]
        for event in events:
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
                event = LogEvent(event.dt, 'message', d, 'message', event.line)
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
                    es = '%s LogFile put Event [%s] in %s'
                    ###
                    # Don't process junk events, waste of cycles
                    ###
                    if event.category == 'command':
                        listener.command_events.put_nowait(event)
                        queue = 'command'
                    else:
                        listener.generic_events.put_nowait(event)
                        queue = 'generic'
                    t = (self.zserv.name, event.type, listener.name, queue,
                         event.category)
                    logging.debug((es + "'s %s queue, category: %s") % t)

