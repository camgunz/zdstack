from ZDStack.BaseStatKeeper import BaseStatKeeper
from ZDStack.Listable import Listable
from ZDStack import DATABASE as DB

def parse_player_name(name):
    ###
    # It's a little ridiculous, but people are VERY creative in how they
    # add # their clan/team tags.  So we have a ridiculous algorithm to
    # figure this out.
    ###
    delimiters = {'[': ']', '<': '>', '(': ')', '*': '*', '_': '_',
                  '-': '-', ']': '[', '>': '<', ')': '('}
    seen = []
    waiting = []
    tokens = []
    s = ''
    other_stuff = ''
    in_token = False
    for c in name:
        if c in delimiters.keys(): # found a delimiter
            if waiting and waiting[-1] == c: # found the end of a token
                tokens.append(Token(s, seen[-1], c))
                s = ''
                waiting = waiting[:-1]
                seen = seen[:-1]
                in_token = False
            elif in_token: # found the beginning of a new token
                tokens.append(Token(s, seen[-1]))
                waiting = waiting[:-1]
                seen = seen[:-1]
                seen.append(c)
                s = ''
            else: # found the beginning of a token
                waiting = waiting[:-1]
                seen = seen[:-1]
                seen.append(c)
                waiting.append(delimiters[c])
                # other_stuff += c
                in_token = True
        elif in_token: # add to the current token
            s += c
        else: # not a token
            other_stuff += c
    if s:
        if in_token:
            tokens.append(Token(s, ''.join(seen)))
        else:
            other_stuff += s
    try:
        tokens = sorted([(len(t), t) for t in tokens])
        # tokens.reverse()
        token = tokens[0][1]
        tag = str(token)
        return (tag, name.replace(tag, ''))
    except IndexError: # no tag
        return ('', name)

class Player(BaseStatKeeper):

    def __init__(self, name, zdstack, ip=None):
        BaseStatKeeper.__init__(self)
        self.name = name
        self.ip = ip
        self.escaped_name = self.name.replace('&', "&amp;")
        self.escaped_name = self.escaped_name.replace('<', "&lt;")
        self.escaped_name = self.escaped_name.replace('>', "&gt;")
        self.escaped_name = self.escaped_name.replace("'", "&#39;")
        self.escaped_name = self.escaped_name.replace('"', "&quot;")
        self.homogenized_name = self.name.replace(' ', '').lower()
        self.homogenized_name = self.homogenized_name.replace('\n', '')
        self.homogenized_name = self.homogenized_name.replace('\t', '')
        self.tag, self.player_name = parse_player_name(self.name)
        self.playing = False
        self.team = None
        self.stat_container = self.team
        self.possible_aliases = Listable()
        # If this player has never connected before, insert it into the DB.
        # Grab all the IP addresses for that player name
        # Grab all the player names associated with any of those IP addresses
        # Save that list in self.possible_aliases
        def log_ip(row):
            addresses = row['addresses'].split(',')
            addresses.append(self.ip)
            row['addresses'] = ','.join(addresses)
        def get_ip_match_func(addresses):
            addresses = addresses.split(',')
            s1 = set(addresses.split(','))
            f = lambda x: list(s1.intersection(x.split(',')))
            return lambda r: f(r['addresses'])
        if DB:
            rs = DB.select('players', where=[lambda r: r['name'] == self.name])
            rs = [x for x in rs]
            if not rs:
                DB.insert('players', values=(self.name, self.ip))
            elif self.ip not in row['addresses']:
                DB.update('players', set=[log_ip],
                           where=[lambda r: r['name'] == self.name])
            addresses = rs[0]['addresses'].split(',') + [self.ip]
            for row in DB.select('players',
                                 where=[get_ip_match_func(addresses)]):
                self.possible_aliases.append(row['name'])
        else:
            self.zdstack.log("PyXSE not found, Player => IP Logging disabled")
            
        ###
        # TODO:
        #   - Add latency/packet-loss tracking
        ###

    

    def set_team(self, team):
        self.team = team
        self.stat_container = self.team

