import re
import time
import logging

from datetime import datetime
from collections import deque

from ZDStack.LogEvent import LogEvent
from ZDStack.LineParser import LineParser
from ZDStack.ClientRegexps import Regexps as ClientRegexps
from ZDStack.ServerRegexps import Regexps as ServerRegexps
# from ZDStack.FakeClientRegexps import Regexps as FakeClientRegexps
# from ZDStack.FakeServerRegexps import Regexps as FakeServerRegexps

class LogParser:

    def __init__(self, name, logtype='server', fake=False):
        """Initializes a LogParser.

        name:    a string representing the name of this LogParser.
        logtype: a string representing the type of log to parse.
                 Valid options include 'server' and 'client'.
        fake:    an optional boolean, whether or not this parser is
                 parsing for a fake ZServ.

        """
        self.name = name
        if logtype == 'server':
            logging.debug("Loading ServerRegexps")
            self.lineparser = LineParser(ServerRegexps)
        elif logtype == 'client':
            logging.debug("Loading ClientRegexps")
            self.lineparser = LineParser(ClientRegexps)
        else:
            raise ValueError("Unsupported log type [%s]" % (logtype))

    def __str__(self):
        self.name.join(['<', '>'])

    def __repr__(self):
        return "LogParser('%s')" % (self.name)

    def __call__(self, data):
        return self.parse(data)

    def parse(self, data):
        """Parses data into LogEvents.

        data: a string of log data.

        Returns a 2-Tuple (list of LogEvents, string of leftover data)

        """
        raise NotImplementedError()

    def split_data(self, data):
        """Splits data into tokens that might be events.

        data: a string of log data.

        Returns a 2-Tuple, (deque of split data, leftovers)

        """
        datalines = [x for x in data.splitlines() if x]
        if datalines and not data.endswith('\n'):
            leftovers = datalines[-1]
            datalines = datalines[:-1]
        else:
            leftovers = ''
        lines = deque(datalines)
        return (lines, leftovers)

class ConnectionLogParser(LogParser):

    def __init__(self, log_type='server', fake=False):
        """Initializes a ConnectionLogParser.

        logtype: a string representing the type of log to parse.
                 Valid options include 'server' and 'client'.
        fake:    an optional boolean, whether or not this parser is
                 parsing for a fake ZServ.

        """
        LogParser.__init__(self, "Connection Log Parser", log_type, fake=fake)

    def parse(self, data):
        """Parses data into LogEvents.

        data: a string of log data.

        Returns a 2-Tuple (list of LogEvents, string of leftover data)

        """
        lines, leftovers = self.split_data(data)
        events = []
        while len(lines):
            line = lines.popleft()
            tokens = [x for x in line.split() if x]
            if '\n' in line:
                raise ValueError("Somehow, there is a newline within a line")
            timestamp = ' '.join([tokens[0], tokens[1]])
            time_tup = time.strptime(timestamp, '%Y/%m/%d %H:%M:%S')
            line_dt = datetime(*time_tup[:6])
            parsed_events = self.lineparser.get_event(line_dt, line)
            if parsed_events:
                events.extend(parsed_events)
            elif line.endswith('Connection Log Stopped'):
                d = {'log': 'connection'}
                events.append(LogEvent(line_dt, 'log_roll', d))
            else:
                events.append(LogEvent(line_dt, 'junk', {'data': line}))
        return (events, leftovers)

class GeneralLogParser(LogParser):

    def __init__(self, log_type='server', fake=False):
        """Initializes a GeneralLogParser.

        logtype: a string representing the type of log to parse.
                 Valid options include 'server' and 'client'.
        fake:    an optional boolean, whether or not this parser is
                 parsing for a fake ZServ.

        """
        LogParser.__init__(self, "General Log Parser", log_type, fake=fake)

    def parse(self, data):
        """Parses data into LogEvents.

        data: a string of log data.

        Returns a 2-Tuple (list of LogEvents, string of leftover data)

        """
        now = datetime.now()
        lines, leftovers = self.split_data(data)
        events = []
        while len(lines):
            line = lines.popleft()
            logging.debug("Parsing line [%s]" % (line))
            # events.extend(self.lineparser.get_event(now, line))
            parsed_events = self.lineparser.get_event(now, line)
            if parsed_events:
                events.extend(parsed_events)
            elif line == 'General logging off':
                d = {'log': 'general'}
                events.append(LogEvent(now, 'log_roll', d, line))
            elif line.startswith('<') and '>' in line:
                ###
                # There are certain strings that make it impossible to
                # determine what is a player name and what is a message, for
                # instance:
                #   '<<!> Ladna> > I think that EFL > yr mom >:('
                # Here, the player name should be '<!> Ladna> '.  I know it's
                # stupid, but people can basically use w/e they want for a
                # name, like (>^.^)>, which I actually think is cool (Kirby
                # face!). This is compounded by the fact that people can say
                # w/e they want.
                #
                # So, basically what we do is create a list of possible player
                # names that will be passed to the server.  The first one that
                # matches (this test is done within the server itself) is used.
                # Just a case of dealing with crazy user input.
                ###
                tokens = line.split('>')
                possible_player_names =  [tokens[0][1:]]
                for x in range(1, len(tokens)):
                    possible_player_names.append('>'.join(tokens[:x])[1:])
                line_data = {'contents': line,
                             'possible_player_names': possible_player_names}
                e = LogEvent(now, 'message', line_data, line)
                events.append(e)
            if not events:
                events.append(LogEvent(now, 'junk', {'data': line}, line))
        return (events, leftovers)

class FakeZServLogParser(GeneralLogParser):

    def __init__(self):
        GeneralLogParser.__init__(self, log_type='server', fake=True)
        self.name = 'Fake Log Parser'


