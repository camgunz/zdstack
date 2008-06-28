import re
import time
import logging

from datetime import datetime
from collections import deque

from ZDStack.LogEvent import LogEvent
from ZDStack.LineParser import LineParser
from ZDStack.ClientRegexps import Regexps as ClientRegexps
from ZDStack.ServerRegexps import Regexps as ServerRegexps

class LogParser:

    def __init__(self, name, logtype='server'):
        """Initializes a LogParser.

        name:    a string representing the name of this LogParser.
        logtype: a string representing the type of log to parse.
                 Valid options include 'server' and 'client'.

        """
        self.name = name
        if logtype == 'server':
            self.lineparser = LineParser(ServerRegexps)
        elif logtype == 'client':
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

        Returns a deque of split data.

        """
        return deque([x for x in data.splitlines() if x])

class ConnectionLogParser(LogParser):

    def __init__(self, log_type='server'):
        """Initializes a ConnectionLogParser.

        logtype: a string representing the type of log to parse.
                 Valid options include 'server' and 'client'.

        """
        self.name = "Connection Log Parser"

    def parse(self, data):
        """Parses data into LogEvents.

        data: a string of log data.

        Returns a 2-Tuple (list of LogEvents, string of leftover data)

        """
        lines = self.split_data(data)
        events = []
        leftovers = []
        while len(lines):
            line = lines.popleft()
            tokens = [x for x in line.split() if x]
            if '\n' in line:
                raise ValueError("Somehow, there is a newline within a line")
            d, t, message = tokens[0], tokens[1], ' '.join(tokens[2:])
            timestamp = ' '.join([d, t])
            time_tup = time.strptime(timestamp, '%Y/%m/%d %H:%M:%S')
            line_dt = datetime(*time_tup[:6])
            if line.endswith('Connection Log Stopped'):
                events.append(LogEvent(line_dt, 'log_roll',
                                       {'log': 'connection'}))
            elif line.endswith('has connected'):
                ip_tokens = [x for x in tokens[2:] \
                                    if x.startswith('(') and x.endswith(')')]
                if len(ip_tokens) != 1:
                    es = "Error parsing 'connection' line [%s]"
                    raise ValueError(es % (line))
                ip_token = ip_tokens[0]
                ip = ip_token.strip('()')
                xi = 0
                yi = message.rindex(ip_tokens[0]) - 1
                name = message[xi:yi]
                events.append(LogEvent(line_dt, 'ip_log',
                                       {'player': name, 'ip': ip}))
            elif (len(lines) and data.endswith('\n')) or \
                 'Connection Log Started' in line or \
                 'zserv startup' in line: # line is junk
                events.append(LogEvent(line_dt, 'junk', {'data': line}))
            else: # line was incomplete
                leftovers.append(line)
        return (events, '\n'.join(leftovers))

class GeneralLogParser(LogParser):

    def __init__(self, log_type='server'):
        """Initializes a GeneralLogParser.

        logtype: a string representing the type of log to parse.
                 Valid options include 'server' and 'client'.

        """
        LogParser.__init__(self, "General Log Parser")

    def parse(self, data):
        """Parses data into LogEvents.

        data: a string of log data.

        Returns a 2-Tuple (list of LogEvents, string of leftover data)

        """
        now = datetime.now()
        lines = self.split_data(data)
        events = []
        leftovers = []
        while len(lines):
            line = lines.popleft()
            if line == 'General logging off':
                events.append(LogEvent(now, 'log_roll', {'log': 'general'}))
            events.extend(self.lineparser.get_event(now, line))
            if line.startswith('<') and '>' in line:
                line_type = 'message'
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
                # names that will be passed to # the server.  The first one that
                # matches (this test is done within the server # itself) is used.
                # Just a case of dealing with crazy user input.
                ###
                tokens = line.split('>')
                possible_player_names =  [tokens[0][1:]]
                for x in range(1, len(tokens)):
                    possible_player_names.append('>'.join(tokens[:x])[1:])
                line_data = {'contents': line,
                             'possible_player_names': possible_player_names}
                e = LogEvent(now, 'message', line_data)
                events.append(e)
            if not events:
                events.append(LogEvent(now, 'junk', {'data': line}))
        return (events, '\n'.join(leftovers))

