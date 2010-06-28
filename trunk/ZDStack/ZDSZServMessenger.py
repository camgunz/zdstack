from __future__ import with_statement

import threading

from ZDStack import get_zdslog

zdslog = get_zdslog()

class Messenger(object):

    TIMEOUT = 5 # in seconds

    def __init__(self, zserv):
        self.zserv = zserv
        self.lock = threading.Lock()
        self.response_events = []
        self.response_started = threading.Event()
        self.response_finished = threading.Event()
        self.response_processed = threading.Event()
        self.event_response_type = None

    def __write(self, message):
        self.zserv.zserv.stdin.write(message + '\n')
        self.zserv.zserv.stdin.flush()

    def clear(self):
        self.response_events = []
        zdslog.debug('Clearing response_started')
        self.response_started.clear()
        zdslog.debug('Clearing response_finished')
        self.response_finished.clear()
        zdslog.debug('Setting response_processed')
        self.response_processed.set()
        self.event_response_type = None

    @property
    def is_waiting_for_response(self):
        return self.event_response_type is not None

    @property
    def has_received_response_data(self):
        return self.response_started.isSet()

    @property
    def is_processing_response(self):
        return not self.response_processed.isSet()

    def is_waiting_for(self, event_type):
        return event_type == self.event_response_type

    def send(self, message, event_response_type=None, handler=None):
        """Sends a message to the running zserv process.

        :param message: the message to send (cannot contain newlines)
        :type message: string
        :param event_response_type: the type of event to wait for in
                                    response
        :type event_response_type: string
        :param handler: optional, a function that will be called with
                        the received events as arguments (all in a
                        list)
        :type handler: function
        :returns: a sequence of :class:`~ZDStack.LogEvent` instances,
                  or whatever the handler function returns, if given

        It should be noted that this is a synchronous method, i.e. that
        commands are sent to the ZServ and processed synchronously.

        """
        if '\n' in message or '\r' in message:
            es = "Message cannot contain newlines or carriage returns"
            raise ValueError(es)
        if not self.zserv.is_running():
            zdslog.error("Cannot send data to a stopped ZServ")
            return self.clear()
        with self.lock:
            self.response_processed.clear()
            self.event_response_type = event_response_type
            self.__write(message)
            if not self.zserv.events_enabled or event_response_type is None:
                return self.clear()
            zdslog.debug('Waiting for response from command [%s]' % (message))
            self.response_started.wait(self.TIMEOUT)
            if not self.response_started.isSet():
                self.clear()
                raise Exception('Timed out waiting for a response to start')
            self.response_finished.wait(self.TIMEOUT)
            if not self.response_finished.isSet():
                self.clear()
                raise Exception('Timed out waiting for a response to finish')
            ###
            # I'm not totally happy about this hack, but so be it.
            ###
            if message == 'players':
                self.response_events = [
                    x for x in self.response_events if 'player_num' in x.data
                ]
            try:
                if handler:
                    output = handler(self.response_events)
                else:
                    output = [x for x in self.response_events]
            except:
                self.clear()
                raise
            self.clear()
            zdslog.debug('Returning [%s]' % (output))
            return output

