from sqlalchemy import relation, and_
from sqlalchemy.orm import mapper

import logging

from base64 import b64encode

from ZDStack import get_engine
from ZDStack.Utils import parse_player_name, homogenize, html_escape
from ZDStack.ZDSTables import *

class Wad(object): pass
class Map(object): pass
class Weapon(object): pass
class Port(object): pass
class GameMode(object): pass
class Round(object): pass

class Team(object):

    def __init__(self, x):
        self.color = self.name = x

class Player(object):

    def __init__(self, ip_address, port, name=None):
        """Initializes a BasePlayer.

        ip_address: a string representing the IP address of the player
        port:       a string representing the port of the player
        name:       optional, a string representing the name of the
                    player

        """
        logging.debug('name: [%s]' % (name))
        self.ip = ip_address
        self.port = port
        self.number = None
        self.name = ''
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
            ###
            return
        self.name = name
        self.tag, self.player_name = parse_player_name(self.name)
        self.homogenized_name = homogenize(self.name)
        self.escaped_name = html_escape(self.name)
        self.escaped_homogenized_name = html_escape(self.homogenized_name)
        self.encoded_name = b64encode(self.name)
        self.homogenized_player_name = homogenize(self.player_name)
        self.escaped_player_name = html_escape(self.player_name)
        self.escaped_homogenized_player_name = \
                                    html_escape(self.homogenized_player_name)
        if self.tag is None:
            self.homogenized_tag = None
            self.escaped_tag = None
            self.escaped_homogenized_tag = None
        else:
            self.homogenized_tag = homogenize(self.tag)
            self.escaped_tag = html_escape(self.tag)
            self.escaped_homogenized_tag = html_escape(self.homogenized_tag)

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

    def __str__(self):
        return "<Player [%s]>" % (self.name)

    def __repr__(self):
        return "Player(%s)" % (self.name)

class Alias(object): pass
class PlayerAddress(object): pass
class Frag(object): pass
class FlagTouch(object): pass
class FlagReturn(object): pass

mapper(Wad, wad_table, properties={'maps': relation(Map, backref='wad')})
mapper(Map, map_table, properties={'rounds': relation(Round, backref='map')})
mapper(Weapon, weapon_table, properties={'frags': relation(Frag, backref='weapon')})
mapper(Port, port_table, properties={'game_modes': relation(GameMode, backref='port')})
mapper(GameMode, game_mode_table, properties={'rounds': relation(Round, backref='game_mode')})
mapper(Round, round_table, properties={'frags': relation(Frag, backref='round'),
                                       'flag_touches': relation(FlagTouch, backref='round'),
                                       'flag_returns': relation(FlagReturn, backref='round'),
                                       'players': relation(Alias, secondary=round_alias_table, backref='rounds')})
mapper(Team, team_table, properties={'frags': relation(Frag, backref='team'),
                                     'flag_touches': relation(FlagTouch, backref='team'),
                                     'flag_returns': relation(FlagReturn, backref='team')})
mapper(Player, player_table, properties={'aliases': relation(Alias, secondary=player_alias_table, backref='players')})
mapper(Alias, alias_table, properties={'ip_addresses': relation(PlayerAddress, backref='player',
                                       'frags': relation(Frag, primaryjoin=and_(player_table.c.id == frag_table.c.fragger_id,
                                                                                frag_table.c.fragger_id != frag_table.c.fraggee_id),
                                                               backref='fragger'),
                                       'deaths': relation(Frag, primaryjoin=player_table.c.id == frag_table.c.fraggee_id, backref='fraggee'),
                                       'flag_touches': relation(FlagTouch, backref='player'),
                                       'flag_returns': relation(FlagReturn, backref='player'),
                                       'flag_picks': relation(FlagTouch, primaryjoin=and_(player_table.c.id == flag_touch_table.c.player_id,
                                                                                          flag_touch_table.c.was_picked == True)),
                                       'flag_caps': relation(FlagTouch, primaryjoin=and_(player_table.c.id == flag_touch_table.c.player_id,
                                                                                         flag_touch_table.c.resulted_in_score == True)),
                                       'flag_pick_caps': relation(FlagTouch, primaryjoin=and_(player_table.c.id == flag_touch_table.c.player_id,
                                                                                              flag_touch_table.c.was_picked == True)),
                                                                                              flag_touch_table.c.resulted_in_score == True))})
mapper(PlayerAddress, player_address_table)
mapper(Frag, frag_table)
mapper(FlagTouch, flag_touch_table)
mapper(FlagReturn, flag_return_table)

