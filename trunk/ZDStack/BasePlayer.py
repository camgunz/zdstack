from base64 import b64decode, b64encode

from ZDStack.BaseStatKeeper import BaseStatKeeper
from ZDStack.Listable import Listable
from ZDStack import get_database

def homogenize(s):
    return s.replace(' ', '').lower().replace('\n', '').replace('\t', '')

class Token:

    def __init__(self, contents, opener='', closer=''):
        self.contents = contents
        self.opener = opener
        self.closer = closer
        self.__length = len(self.contents)
        self.__string = ''.join([self.opener, self.contents, self.closer])
        self.homogenized_contents = homogenize(contents)

    def __str__(self):
        return self.__string

    def __len__(self):
        return self.__length

    def __eq__(self, token):
        try:
            return self.homogenized_contents == token.homogenized_contents
        except AttributeError:
            return False

def parse_player_name(name):
    ###
    # It's a little ridiculous, but people are VERY creative in how they
    # add their clan/team tags.  So we have a ridiculous algorithm to
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
        return (None, name)

def html_escape(s):
    # Basically ripped from web.py
    t = s.replace('&', "&amp;")
    t = t.replace('<', "&lt;")
    t = t.replace('>', "&gt;")
    t = t.replace("'", "&#39;")
    t = t.replace('"', "&quot;")
    return t

class BasePlayer(BaseStatKeeper):

    def __init__(self, name, zserv, ip=None):
        BaseStatKeeper.__init__(self)
        self.name = name
        self.zserv = zserv
        self.ip = ip
        self.tag, self.player_name = parse_player_name(self.name)
        self.homogenized_name = homogenize(self.name)
        self.escaped_name = html_escape(self.name)
        self.escaped_homogenized_name = html_escape(homogenize(self.name))
        self.encoded_name = b64encode(self.name)
        self.homogenized_player_name = homogenize(self.player_name)
        self.escaped_player_name = html_escape(self.player_name)
        self.escaped_homogenized_player_name = \
                                    html_escape(homogenize(self.player_name))
        if self.tag is not None:
            self.homogenized_tag = homogenize(self.tag)
            self.escaped_tag = html_escape(self.tag)
            self.escaped_homogenized_tag = html_escape(homogenize(self.tag))
        else:
            self.homogenized_tag = None
            self.escaped_tag = None
            self.escaped_homogenized_tag = None
        self.set_map(self.zserv.map)
        self.stat_container = self.zserv.map
        self.playing = False
        self.disconnected = False
        db = get_database()
        # If this player has never connected before, insert it into the db.
        if self.ip:
            if db:
                rs = db.select('players',
                               where=[lambda r: r['name'] == self.encoded_name])
                rs = [x for x in rs]
                if not rs:
                    db.insert('players', values=(self.encoded_name, self.ip))
                addresses = set()
                for r in rs:
                    for address in r['addresses'].split(','):
                        addresses.add(address)
                if self.ip not in addresses:
                    def log_ip(row):
                        a = row['addresses'].split(',')
                        a.append(self.ip)
                        s = set()
                        a = [x for x in a if x not in s and not s.add(x)]
                        row['addresses'] = ','.join(a)
                    db.update('players', set=[log_ip],
                               where=[lambda r: r['name'] == self.encoded_name])
            else:
                es = "PyXSE not found, Player => IP matching unavailable"
                self.zserv.log(es)
        ###
        # TODO:
        #   - Add latency/packet-loss tracking
        ###

    def get_possible_aliases(self):
        db = get_database()
        if not db:
            self.zserv.log("PyXSE not found, Player => IP Logging disabled")
            return None
        def get_ip_match_func(addresses):
            # Takes a set() of strings representing IP addresses
            f = lambda x: list(addresses.intersection(x.split(',')))
            return lambda r: f(r['addresses'])
        names = set([self.encoded_name])
        addresses = set([])
        if self.ip:
            addresses.add(self.ip)
        number_of_names = len(names)
        rs = db.select('players', where=[lambda r: r['name'] in names])
        for r in rs:
            for address in r['addresses'].split(','):
                addresses.add(address)
        else:
            es = "[%s] does not exist in db"
            self.zserv.log(es % (self.name))
        number_of_addresses = len(addresses)
        if number_of_addresses:
            rs = db.select('players', where=[get_ip_match_func(addresses)])
            for r in rs:
                for address in r['addresses'].split(','):
                    addresses.add(address)
                names.add(r['name'])
        while len(names) != number_of_names and \
              len(addresses) != number_of_addresses: # names/addresses were added
            number_of_names = len(names)
            number_of_addresses = len(addresses)
            rs = db.select('players', where=[lambda r: r['name'] in names])
            for r in rs:
                for address in r['addresses'].split(','):
                    addresses.add(address)
            if number_of_addresses:
                rs = db.select('players', where=[get_ip_match_func(addresses)])
                for r in rs:
                    for address in r['addresses'].split(','):
                        addresses.add(address)
                    names.add(r['name'])
        return sorted([b64decode(x) for x in list(names)])

    def exportables(self):
        out = []
        for x in BaseStatKeeper.exportables(self):
            if x[0] != 'team' and \
              (('team' in self and x[1] != self.team) or \
               ('team' not in self)) and \
               x[0] != 'map' and \
              (('map' in self and x[1] != self.map) or \
               ('map' not in self)) and \
               x[0] != 'zserv' and \
              (('zserv' in self and x[1] != self.zserv) or \
               ('zserv' not in self)):
                out.append(x)
        possible_aliases = self.get_possible_aliases()
        if possible_aliases:
            out.append(('possible_player_aliases', Listable(possible_aliases)))
        else:
            out.append(('possible_player_aliases', None))
        return out

    def set_map(self, map):
        self.map = map
        self.stat_container = self.map

    def __str__(self):
        return "<Player [%s]>" % (self.name)

    def __repr__(self):
        return "Player(%s)" % (self.name)

