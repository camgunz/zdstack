import re
import time
from datetime import datetime
from collections import deque

from ZDStack.LogEvent import LogEvent

class LogParser:

    def __init__(self, name, logtype='server'):
        self.name = name
        if type == 'server':
            from ZDStack.ServerRegexps import *
        elif type == 'client':
            from ZDStack.ClientRegexps import *
        else:
            raise ValueError("Unsupported log type [%s]" % (logtype))

    def __str__(self):
        self.name.join(['<', '>'])

    def __repr__(self):
        return "LogParser('%s')" % (self.name)

    def __call__(self, data):
        return self.parse(data)

    def parse(self, data):
        raise NotImplementedError()

    def split_data(self, data):
        return deque([x for x in data.splitlines() if x])

class ConnectionLogParser(LogParser):

    def __init__(self):
        self.name = "Connection Log Parser"

    def parse(self, data):
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

    def __init__(self):
        LogParser.__init__(self, "General Log Parser")

    def parse(self, data):
        now = datetime.now()
        lines = self.split_data(data)
        events = []
        leftovers = []
        while len(lines):
            line = lines.popleft()
            tokens = line.split(' ')
            death_event = line_to_death_event(now, line)
            connection_event = line_to_connection_event(now, line)
            join_event = line_to_join_event(now, line)
            rcon_event = line_to_rcon_event(now, line)
            flag_event = line_to_flag_event(now, line)
            map_event = line_to_map_event(now, line)
            if line == 'General logging off':
                events.append(LogEvent(now, 'log_roll', {'log': 'general'}))
            elif death_event:
                events.append(death_event)
            elif connection_event:
                events.append(connection_event)
            elif join_event:
                events.append(join_event)
            elif rcon_event:
                events.append(rcon_event)
            elif flag_event:
                events.append(flag_event)
            elif map_event:
                events.append(map_event)
            elif line.startswith('<') and '>' in line and ':' in line:
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
            else:
                events.append(LogEvent(now, 'junk', {'data': line}))
        return (events, '\n'.join(leftovers))
