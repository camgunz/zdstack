import time
from datetime import datetime
from collections import deque

from ZDStack.LogEvent import LogEvent

NUMS_TO_WEAPONS = {'1': 'fist', '2': 'chainsaw', '3': 'pistol',
                   '4': 'shotgun', '5': 'super shotgun', '6': 'chaingun',
                   '7': 'rocket launcher', '8': 'plasma rifle', '9': 'bfg',
                   '12': 'rocket suicide'}

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
            if line.endswith('has connected'):
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
                events.append(LogEvent(line_dt, 'connection',
                                       {'player': name, 'ip': ip}))
            elif line.endswith('disconnected'):
                tokens = [x for x in line.split() if x]
                # ending_token = tokens.index('disconnected')
                # name = tokens[2:ending_token]
                e = LogEvent(line_dt, 'disconnection',
                             {'player': ' '.join(tokens[2:-1])})
                events.append(e)
            elif 'joined the game on the' in message:
                token = ' joined the game on the '
                xi = message.rindex(token)
                name = message[:xi]
                team = message[xi+len(token):-6].lower() # ends with a '.'
                e = LogEvent(line_dt, 'game_join',
                             {'player': name, 'team': team})
                events.append(e)
            elif (len(lines) and data.endswith('\n')) or \
                 'Connection Log Started' in line or \
                 'zserv startup' in line: # line is junk
                events.append(LogEvent(line_dt, 'junk', {'data': line}))
            else: # line was incomplete
                leftovers.append(line)
        return (events, '\n'.join(leftovers))

class WeaponLogParser(LogParser):

    def __init__(self):
        self.name = "Weapon Log Parser"

    def parse(self, data):
        now = datetime.now()
        lines = self.split_data(data)
        events = []
        leftovers = []
        while len(lines):
            line = lines.popleft()
            tokens = [x for x in line.split('\\') if x]
            if not len(tokens) == 3:
                if len(lines) or data.endswith('\n'): # line was junk
                    events.append(LogEvent(now, 'junk', {'data': line}))
                else:
                    leftovers.append(line)
                    raise ValueError("Error parsing line [%s]" % (line))
                continue
            e = LogEvent(now, 'frag', {'fragger': tokens[0],
                                       'fraggee': tokens[1],
                                       'weapon': NUMS_TO_WEAPONS[tokens[2]]})
            events.append(e)
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
            if 'RCON' in line and line.startswith('RCON'):
                if line.endswith('denied!'):
                    line_type = 'rcon_denied'
                    line_data = {'player': ' '.join(tokens[2:-2])}
                    events.append(LogEvent(now, line_type, line_data))
                elif line.endswith('granted!'):
                    line_type = 'rcon_granted'
                    line_data = {'player': ' '.join(tokens[2:-2])}
                    events.append(LogEvent(now, line_type, line_data))
                else:
                    events.append(LogEvent(now, junk, {'data': line}))
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
            elif 'RCON' in line and ' RCON (' in line and ' )' in line:
                line_type = 'rcon_action'
                line_data = \
                        {'action': line[line.rindex('(')+1:line.rindex(')')-1],
                         'player': line[:line.rindex('RCON')].strip()}
                events.append(LogEvent(now, line_type, line_data))
            elif 'is now on the' in line:
                token = ' is now on the '
                xi = line.rindex(token)
                player = line[2:xi]
                team = line[xi+len(token):-5].lower().replace('.', '').strip()
                e = LogEvent(now, 'team_switch',
                             {'player': player, 'team': team})
                events.append(e)
            # RCON for <!>Ladna is denied!
            # RCON for <!>Ladna is granted!
            # <!>Ladna RCON (map map02 )
            elif 'flag' in line:
                if 'has taken the' in line:
                    line_type = 'flag_touch'
                    line_data = {'player': ' '.join(tokens[1:-5])}
                    events.append(LogEvent(now, line_type, line_data))
                elif 'lost the' in line:
                    line_type = 'flag_loss'
                    line_data = {'player': ' '.join(tokens[1:-4])}
                    events.append(LogEvent(now, line_type, line_data))
                elif 'returned the' in line:
                    line_type = 'flag_return'
                    line_data = {'player': ' '.join(tokens[1:-4])}
                    events.append(LogEvent(now, line_type, line_data))
                elif 'picked up the' in line:
                    line_type = 'flag_pick'
                    line_data = {'player': ' '.join(tokens[1:-5])}
                    events.append(LogEvent(now, line_type, line_data))
            elif 'scored for the' in line:
                line_type = 'flag_cap'
                line_data = {'player': ' '.join(tokens[1:-5]),
                             'team': tokens[-2].lower()}
                events.append(LogEvent(now, line_type, line_data))
            elif line.startswith('map'):
                map_number = int(line[:line.index(': ')][3:])
                map_name = line[line.index(': ')+2:]
                line_data = {'number': map_number, 'name': map_name}
                e = LogEvent(now, 'map_change', line_data)
                events.append(e)
            else:
                events.append(LogEvent(now, 'junk', {'data': line}))
        return (events, '\n'.join(leftovers))

