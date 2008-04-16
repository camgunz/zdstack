import re
import time
from datetime import datetime
from collections import deque

from ZDStack.LogEvent import LogEvent

NUMS_TO_WEAPONS = {'1': 'fist', '2': 'chainsaw', '3': 'pistol',
                   '4': 'shotgun', '5': 'super shotgun', '6': 'chaingun',
                   '7': 'rocket launcher', '8': 'plasma rifle', '9': 'bfg',
                   '10': 'telefrag', '11': 'unknown', '12': 'suicide',
                   '13': 'telefuck'}

REGEXPS_AND_WEAPONS = \
    [(r"^> (.*) chewed on (.*)'s fist.$", 'fist'),
     (r"^> (.*) was mowed over by (.*)'s chainsaw.$", 'chainsaw'),
     (r"^> (.*) was tickled by (.*)'s pea shooter.$", 'pistol'),
     (r"^> (.*) chewed on (.*)'s boomstick.$", 'shotgun'),
     (r"^> (.*) was mowed down by (.*)'s chaingun.$", 'chaingun'),
     (r"^> (.*) was splattered by (.*)'s super shotgun.$", 'super shotgun'),
     (r"^> (.*) rode (.*)'s rocket.$", 'rocket launcher'),
     (r"^> (.*) was melted by (.*)'s plasma gun.$", 'plasma gun'),
     (r"^> (.*) couldn't hide from (.*)'s BFG.$", 'bfg'),
     (r"^> (.*) was splintered by (.*)'s BFG.$", 'bfg'),
     (r"^> (.*) was telefragged by (.*).$", 'telefrag')]

REGEXPS_AND_DEATHS = \
    [(r"^> (.*) should have stood back.$", 'rocket suicide'),
     (r"^> (.*) mutated.$", 'mutation'),
     (r"^> (.*) melted.$", 'melting'),
     (r"^> (.*) killed himself.$", 'suicide'),
     (r"^> (.*) fell too far.$", 'falling'),
     (r"^> (.*) tried to leave.$", "exiting"),
     (r"^> (.*) can't swim.$", "drowning"),
     (r"^> (.*) checks his glasses.$", 'teamkill')]

REGEXPS_AND_JOINS = \
    [(r"^> (.*) is now on the (Blue|Red|White|Green) team.$", 'team_switch'),
     (r"^> (.*) joined the game.$", 'game_join'),
     (r"^> (.*) joined the game on the (Blue|Red|White|Green) team.$", 'team_join')]

REGEXPS_AND_RCONS = \
    [(r"^RCON for (.*) is denied!$", 'rcon_denied'),
     (r"^RCON for (.*) is granted!$", 'rcon_granted'),
     (r"^(.*) RCON \((.*) \)$", 'rcon_action')]

REGEXPS_AND_FLAGS = \
    [(r"^> (.*) has taken the (.*) flag", 'flag_touch'),
     (r"^> (.*) lost the (.*) flag", 'flag_loss'),
     (r"^> (.*) returned the (.*) flag", 'flag_return'),
     (r"^> (.*) picked up the (.*) flag", 'flag_pick'),
     (r"^> (.*) scored for the (.*) team", 'flag_cap')]

def line_to_death_event(event_dt, line):
    for regexp, weapon in REGEXPS_AND_WEAPONS:
        match = re.match(regexp, line)
        if match:
            d = {'fragger': match.group(2), 'fraggee': match.group(1),
                 'weapon': weapon}
            return LogEvent(event_dt, 'frag', d)
    for regexp, death in REGEXPS_AND_DEATHS:
        match = re.match(regexp, line)
        if match:
            d = {'fragger': match.group(1), 'fraggee': match.group(1),
                 'weapon': death}
            return LogEvent(event_dt, 'death', d)

def line_to_connection_event(event_dt, line):
    match = re.match(r"^> (.*) has connected.$", line)
    if match:
        d = {'player': match.group(1)}
        return LogEvent(event_dt, 'connection', d)
    match = re.match(r"^> (.*) disconnected$", line)
    if match:
        d = {'player': match.group(1)}
        return LogEvent(event_dt, 'disconnection', d)

def line_to_join_event(event_dt, line):
    for regexp, join in REGEXPS_AND_JOINS:
        match = re.match(regexp, line)
        if match:
            d = {'player': match.group(1)}
            if join.startswith('team'):
                d['team'] = match.group(2).lower()
            return LogEvent(event_dt, join, d)

def line_to_rcon_event(event_dt, line):
    for regexp, rcon in REGEXPS_AND_RCONS:
        match = re.match(regexp, line)
        if match:
            d = {'player': match.group(1)}
            if rcon == 'rcon_action':
                d['action'] = match.group(2)
            return LogEvent(event_dt, rcon, d)

def line_to_flag_event(event_dt, line):
    for regexp, flag in REGEXPS_AND_FLAGS:
        match = re.match(regexp, line)
        if match:
            return LogEvent(event_dt, flag, {'player': match.group(1)})

def line_to_map_event(event_dt, line):
    match = re.match('^map(.*): (.*)$', line)
    if match:
        d = {'name': match.group(2), 'number': int(match.group(1))}
        return LogEvent(event_dt, 'map_change', d)
                        

class LogParser:

    def __init__(self, name):
        self.name = name

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
