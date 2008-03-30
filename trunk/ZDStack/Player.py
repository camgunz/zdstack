from ZDStack.Dictable import Dictable
from ZDStack.Listable import Listable

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

class Player(Dictable):

    def __init__(self, name, zdstack, ip=None):
        Dictable.__init__(self)
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
        self.frags = Listable()
        self.deaths = Listable()
        self.flag_drops = Listable()
        self.playing = False
        self.has_flag = False
        self.team = None
        self.rcon_denials = 0
        self.rcon_accesses = 0
        self.rcon_actions = 0
        self.flag_returns = 0
        self.flag_losses = 0
        self.flag_caps = 0
        self['name'] = self.name
        self['ip'] = self.ip
        self['escaped_name'] = self.escaped_name
        self['homogenized_name'] = self.homogenized_name
        self['self.player_name'] = self.player_name
        self['tag'] = self.tag
        self['frags'] = self.frags
        self['deaths'] = self.frags
        self['flag_drops'] = self.name
        self['playing'] = self.playing
        self['has_flag'] = self.has_flag
        self['team'] = self.team
        self['rcon_denials'] = self.rcon_denials
        self['rcon_accesses'] = self.rcon_accesses
        self['rcon_actions'] = self.rcon_actions
        self['flag_returns'] = self.flag_returns
        self['flag_losses'] = self.flag_losses
        self['flag_caps'] = self.flag_caps

