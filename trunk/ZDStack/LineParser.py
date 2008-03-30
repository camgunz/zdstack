import time
from datetime import datetime

NUMS_TO_WEAPONS = {'1': 'fist', '2': 'chainsaw', '3': 'pistol',
                   '4': 'shotgun', '5': 'super shotgun', '6': 'chaingun',
                   '7': 'rocket launcher', '8': 'plasma rifle', '9': 'bfg'}

class LineParser:

    def __init__(self, name):
        self.name = name

    def __str__(self):
        self.name.join(['<', '>'])

    def __repr__(self):
        return "LineParser('%s')" % (self.name)

    def __call__(self, line):
        return self.parse(line)

    def parse(self, line):
        raise NotImplementedError()

class ConnectionLineParser(LineParser):

    def __init__(self):
        self.name = "Connection Line Parser"

    def parse(self, line):
        tokens = line.split(' ')
        d, t, message = tokens[0], tokens[1], ' '.join(tokens[2:])
        line_dt = datetime(*(time.strptime('%Y/%m/%d %H:%M:%S',
                                           ' '.join([d, t]))))
        if message.endswith('has connected'):
            line_type = 'connection'
            ip_tokens = [x for x in tokens[2:] \
                                    if x.startswith('(') and x.endswith(')')]
            if len(ip_tokens) != 1:
                es = "Error parsing 'connection' line [%s]"
                raise ValueError(es % (line))
            ip = ip_tokens[0].strip('()')
            name = ' '.join(tokens[2:] + tokens[:tokens.index(ip_tokens[0])])
            line_data = {'player': name, 'ip'; ip}
        elif message.endswith('disconnected')
            line_type = 'disconnection'
            line_data = {'player': ' '.join(tokens[2:] + tokens[:-1])}
        elif 'joined the game on the' in message:
            line_type = 'game_join'
            name = ' '.join(tokens[2:] + tokens[:-7])
            team = tokens[-2].lower()
            line_data = {'player': name, 'team': team}
        else:
            line_type = 'junk'
            line_data = {}
        return LogEvent(line_dt, line_type, line_data)

class WeaponLineParser(LineParser):

    def __init__(self):
        self.name = "Weapon Line Parser"

    def parse(self, line):
        now = datetime.now()
        tokens = [x for x in line.split('\\') if x]
        if not len(tokens) == 3:
            raise ValueError("Error parsing line [%s]" % (line))
        line_data = {'fragger': tokens[0], 'fraggee': tokens[1],
                     'weapon': NUMS_TO_WEAPONS[tokens[2]]}
        return LogEvent(now, 'frag', line_data)

class GeneralLineParser(LineParser):

    def __init__(self):
        LineParser.__init__(self, "General Line Parser")

    def parse(self, line):
        now = datetime.now()
        tokens = line.split(' ')
        if line.startswith('<'):
            line_type = 'message'
            ###
            # There are certain strings that make it impossible to determine
            # what # is a player name and what is a message, for instance:
            # '<<!> Ladna> > I think that EFL > yr mom >:('
            # Here, the player name should be '<!> Ladna> >'.  I know it's
            # stupid, # but people can basically use w/e they want for a name,
            # like (>^.^)>, # which I actually think is cool (Kirby face!).
            # This is compounded by # the fact that people can say w/e they
            # want.
            # So, basically what we do is process every character, and create a
            # list of possible player names that will be passed to the server.
            # The first one that matches (this test is done within the server
            # itself) is used.  Just a case of dealing with crazy user input.
            ###
            line_data = {'contents': line, 'possible_player_names': []}
            tag_level = 0
            tag = []
            for c in line:
                if c == '<'
                    if tag_level:
                        tag.append(c)
                    tag_level += 1
                elif c == ' ' and tag[-1] == '>':
                    line_data['possible_player_names'].append(tag[:-1])
        elif 'is now on the' in line:
            player = line[:line.rindex(' is now on the')]
            team = line[:line.rindex(' team')]
            line_type = 'team_switch'
            line_data = {'player': player, 'team': team})
        elif 'RCON' in line:
            if line.startswith('RCON'):
                if line.endswith('denied!'):
                    line_type = 'rcon_denied'
                    line_data = {'player': ' '.join(tokens[2:] + tokens[:-2])}
                elif line.endswith('granted!'):
                    line_type = 'rcon_granted'
                    line_data = {'player': ' '.join(tokens[2:] + tokens[:-2])}
                else:
                    raise ValueError("Error parsing line [%s]" % (line))
            else:
                line_name = 'rcon_action'
                line_data = {'action': line[line.rindex('('):line.rindex(')')],
                             'player': line[:line.rindex('RCON')].strip()}
        elif 'flag' in line:
            if 'has taken the' in line:
                line_type = 'flag_touch'
                line_data = {'player': ' '.join(tokens[:-5])}
            elif 'lost the' in line:
                line_type = 'flag_loss'
                line_data = {'player': ' '.join(tokens[:-4])}
            elif 'scored for the': in line:
                line_type = 'flag_cap':
                line_data = {'player': ' '.join(tokens[:-5]),
                             'team': tokens[-2].lower()}
            elif 'returned the' in line:
                line_type = 'flag_return':
                line_data = {'player': ' '.join(tokens[:-4]),
        elif line == \
"""======================================================================""":
            line_type = 'map_change'
            line_data = {}
        else:
            line_type = 'junk'
            line_data = {}
        return LogEvent(now, line_type, line_data)

