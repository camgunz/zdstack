import csv
import logging

from base64 import b64encode

from ZDStack.Utils import parse_player_name, homogenize, html_escape, get_ratio
from ZDStack.Listable import Listable
from ZDStack.PlayerDB import save_player_ip, get_possible_aliases
from ZDStack.BaseStatKeeper import BaseStatKeeper


class BasePlayer(BaseStatKeeper):

    """Base Player class, holds stats and info for a player."""

    def __init__(self, zserv, ip_address, port, name=None, log_ip=True):
        """Initializes a BasePlayer.

        zserv:      a ZServ instance
        ip_address: a string representing the IP address of the player
        port:       a string representing the port of the player
        name:       optional, a string representing the name of the
                    player
        log_ip:     if True, will log this Player's IP.  True by
                    default.

        """
        logging.debug('name: [%s]' % (name))
        BaseStatKeeper.__init__(self)
        self.zserv = zserv
        self.ip = ip_address
        self.port = port
        self.number = None
        self.name = ''
        self.log_ip = log_ip
        self.tag = None
        self.player_name = ''
        self.homogenized_name = ''
        self.escaped_name = ''
        self.escaped_homogenized_name = ''
        self.encoded_name = ''
        self.homogenized_player_name = ''
        self.escaped_player_name = ''
        self.escaped_homogenized_player_name = ''
        if name:
            self.set_name(name)
        self.set_map(self.zserv.map)
        self.stat_container = self.zserv.map
        self.playing = False
        self.disconnected = False
        ###
        # TODO:
        #   - Add latency/packet-loss tracking
        ###

    def set_name(self, name):
        """Sets this player's name.

        name: a string representing the new name of this player

        """
        if self.name == name:
            ###
            # Why go through all this work if there's been no change?
            return
        self.name = name
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
        if self.log_ip:
            save_player_ip(self.name, self.ip)

    def __ne__(self, x):
        try:
            return not (self.port == x.port and self.ip == x.ip)
        except NameError:
            return True

    def __eq__(self, x):
        try:
            return (self.port == x.port and self.ip == x.ip)
        except NameError:
            return False

    def exportables(self):
        """Returns a list of strings representing exportable values."""
        # logging.debug('')
        out = []
        for x in BaseStatKeeper.exportables(self):
            if x[0] != 'map' and \
              (('map' in self and x[1] != self.map) or \
               ('map' not in self)) and \
               x[0] != 'zserv' and \
              (('zserv' in self and x[1] != self.zserv) or \
               ('zserv' not in self)):
                out.append(x)
        if self.log_ip:
            possible_aliases = \
                    get_possible_aliases(self.name, self.encoded_name, [self.ip])
        else:
            possible_aliases = None
        if possible_aliases:
            out.append(('possible_player_aliases', Listable(possible_aliases)))
        else:
            out.append(('possible_player_aliases', None))
        return out

    def set_map(self, map):
        """Sets this player's map.

        map: a Map instance to set.

        """
        # logging.debug('')
        self.map = map
        self.stat_container = self.map

    def __str__(self):
        return "<Player [%s]>" % (self.name)

    def __repr__(self):
        return "Player(%s)" % (self.name)

    def export_summary(self):
        """Exports a summary of player stats as a dict."""
        ###
        # Values:
        #   Player, Overall Frag/Death Ratio,
        #   Per-Weapon Frags/Deaths/Ratio, Per-Player Frags/Deaths/Ratio
        #   Flag Take/Cap Ratio, Flag Drop/Return Ratio, 
        ###
        d = self.export()
        weapons = sorted(d['weapons'].keys())
        adversaries = sorted(d['adversaries'].keys())
        columns = ['Player', 'Frag/Death %']
        values = [self.name, get_ratio(self.total_frags, self.total_deaths)]
        for weapon in weapons:
            columns.append('Frag with %s' % (weapon))
            columns.append('Death by %s' % (weapon))
            columns.append('Ratio with %s' % (weapon))
            values.append(d['weapons'][weapon]['frags'])
            values.append(d['weapons'][weapon]['deaths'])
            values.append(d['weapons'][weapon]['ratio'])
        for adversary in adversaries:
            columns.append('Fragged %s' % (adversary))
            columns.append('Fragged by %s' % (adversary))
            columns.append('Ratio against %s' % (adversary))
            values.append(d['adversaries'][adversary]['frags'])
            values.append(d['adversaries'][adversary]['deaths'])
            values.append(d['adversaries'][adversary]['ratio'])
        return dict(zip(columns, values))

