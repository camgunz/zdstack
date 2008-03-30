import os
from threading import Thread, Timer

from ZDStack.LogEvent import LogEvent

class LogFile:

    def __init__(self, file_path, log_type, line_parser, listeners=[]):
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
        self.line_parser = line_parser
        self.unprocessed_data = ''
        self.keep_logging = False
        self.listeners = listeners
        self.events = self.get_events()
        Thread(self.log).start()

    def __str__(self):
        return "<%s LogFile %s>" % (self.log_type.capitalize(),
                                    os.path.basename(self.file_path))

    def __repr__(self):
        return "LogFile(%s, %s, %s)" % (self.file_path, self.log_type,
                                        self.line_parser)

    def log(self):
        event = self.events.next()
        while event:
            for listener in self.listeners:
                Thread(listener.handle_event, args=[event]).start()
            event = self.events.next()
        t = Timer(.5, self.log)

    def add_listener(self, listener):
        self.listeners.append(listener)

    def remove_listener(self, listener):
        self.listeners.remove(listener)

    def get_events(self):
        while 1:
            lines = []
            events = []
            current_line = list(self.unprocessed_data)
            for c in self.fobj.read():
                if not c == '\n':
                    current_line.append(c)
                elif current_line:
                    lines.append(''.join(current_line))
                    current_line = []
            self.unprocessed_data += ''.join(current_line)
            for line in lines:
                try:
                    event = self.line_parser.parse(line)
                except Exception, e:
                    event = LogEvent(datetime.now, 'error', str(e))
                events.append(event)
            if not self.listen:
                yield []
            else:
                yield events

