from base64 import b64encode

from ZDStack.Listable import Listable
from ZDStack.PlayerDB import save_player_ip, get_possible_aliases
from ZDStack.BaseStatKeeper import BaseStatKeeper

from ZDStack import parse_player_name, homogenize, html_escape, log

class BasePlayer(BaseStatKeeper):

    def __init__(self, name, zserv, ip=None):
        log("BasePlayer: __init__: name: [%s]" % (name))
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
        if self.tag is None:
            self.homogenized_tag = None
            self.escaped_tag = None
            self.escaped_homogenized_tag = None
        else:
            self.homogenized_tag = homogenize(self.tag)
            self.escaped_tag = html_escape(self.tag)
            self.escaped_homogenized_tag = html_escape(homogenize(self.tag))
        self.set_map(self.zserv.map)
        self.stat_container = self.zserv.map
        self.playing = False
        self.disconnected = False
        if self.ip:
            save_player_ip(self.name, self.ip)
        ###
        # TODO:
        #   - Add latency/packet-loss tracking
        ###

    def exportables(self):
        log("BasePlayer: exportables")
        out = []
        for x in BaseStatKeeper.exportables(self):
            if x[0] != 'map' and \
              (('map' in self and x[1] != self.map) or \
               ('map' not in self)) and \
               x[0] != 'zserv' and \
              (('zserv' in self and x[1] != self.zserv) or \
               ('zserv' not in self)):
                out.append(x)
        possible_aliases = \
                get_possible_aliases(self.name, self.encoded_name, [self.ip])
        if possible_aliases:
            out.append(('possible_player_aliases', Listable(possible_aliases)))
        else:
            out.append(('possible_player_aliases', None))
        return out

    def set_map(self, map):
        log("BasePlayer: set_map")
        self.map = map
        self.stat_container = self.map

    def __str__(self):
        return "<Player [%s]>" % (self.name)

    def __repr__(self):
        return "Player(%s)" % (self.name)

