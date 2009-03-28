import os
import time
import select
import logging
import traceback

from datetime import datetime
from threading import Lock, Event

from ZDStack.Utils import start_thread
from ZDStack.LogEvent import LogEvent

class LogFile:

    """LogFile represents a zserv log file."""

    def __init__(self, log_type, parser, zserv, listeners=[]):
        """Initializes a LogFile instance.

        log_type:  a string representing the kind of LogFile this is,
                   valid options are "client" and "server"
        parser:    a LogParser instance
        zserv:     a ZServ instance
        listeners: a list of LogListener instances to send events to

        """
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
        """Starts logging events."""
        logging.debug("%s starting" % (self.filepath))
        self.keep_logging = True
        self.logging_thread = \
            start_thread(self.log, '%s logging thread' % (self.filepath))

    def stop(self):
        """Stops logging events."""
        self.keep_logging = False
        # self.logging_thread.join()

    def set_filepath(self, filepath, seek_to_end=False):
        """Sets the filepath of the logfile to watch.

        filepath:    a string representing the full path to the new
                     logfile
        seek_to_end: a boolean whether or not to seek to the end of
                     the new logfile

        """
        # logging.debug("Received new filepath [%s]" % (self.filepath))
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
        """Starts watching for a certain event type.

        response_event_type: a string representing the type of event
                             to watch for.

        This method starts watching for a certain event type, and
        stores matching events in self.response_events.  A Logfile
        stops watching for response events only when it finds a
        matching event (or events) and then finds one that doesn't.

        There is also a time out of 1/20 of a second, so this doesn't
        lockup the response mechanism.

        """
        # logging.debug('')
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
        """Returns the list of saved response events."""
        # logging.debug('')
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
        """Watches a file for log events.

        When events are found they are placed in the event queue of
        every listener in self.listeners.

        """
        unprocessed_data = ''
        while self.keep_logging:
            ###
            # We put sleep up at the top to ensure it gets done.  Otherwise
            # CPU usage can go through the roof.
            ###
            ###
            # Consider to switching to a global sleep value that is less than
            # .028 seconds (35Hz).  That keeps us exactly responsive with
            # zserv... even if it's not exactly sync'd with other ports.
            ###
            time.sleep(.05) # higher resolutions burn up CPU unnecessarily
            events = []
            if self.fobj:
                # logging.debug("Fobj was true")
                self.change_file_lock.acquire()
                try:
                    rs, ws, xs = select.select([self.fobj], [], [])
                    for r in rs:
                        unprocessed_data += r.read()
                finally:
                    self.change_file_lock.release()
                if unprocessed_data:
                    try:
                        events, unprocessed_data = \
                                            self.parse(unprocessed_data)
                    except Exception, e:
                        # raise # for debugging
                        tb = traceback.format_exc()
                        ed = {'error': e, 'traceback': tb}
                        events = [LogEvent(datetime.now(), 'error', ed)]
                else:
                    continue
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
                            self.response_finished.set()
                            # notify watch_for_response that we're done
                    for listener in self.listeners:
                        if event.type != 'junk':
                            logging.debug(es % (event.type))
                            s = "Putting %s in %s"
                            logging.debug(s % (event.type,
                                                             listener.name))
                            logging.debug(s % (event.type, listener.name))
                        listener.events.put_nowait(event)
            elif self.filepath and os.path.isfile(self.filepath):
                logging.debug("Creating Fobj")
                self.change_file_lock.acquire()
                try:
                    self.fobj = open(self.filepath)
                finally:
                    self.change_file_lock.release()
            else:
                logging.debug("No Fobj")
                logging.debug("%s: No fobj" % (self.filepath))

