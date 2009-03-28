from elixir import Unicode, DateTime, String, Integer, Entity, Field, \
                   using_options, OneToMany, ManyToOne, ManyToMany, setup_all

from sqlalchemy import and_
from sqlalchemy.orm import mapper, relation

import logging

from base64 import b64encode

from ZDStack import get_engine, get_session
from ZDStack.Utils import parse_player_name, homogenize, html_escape
from ZDStack.ZDSTables import *

class Wad(Entity):

    name = Field(

    def __str__(self):
        return '<Wad %s>' % (self.name)

    def __repr__(self):
        return "Wad('%s')" % (self.name)

class TeamColor(object):

    def __init__(self, x, is_playing=False):
        self.color = self.name = x
        self.is_playing = is_playing

    def __str__(self):
        return self.color

    def __repr__(self):
        return "Team('%s')" % (self.color)

class Map(object):

    def __str__(self):
        return "Map%s: %s" % (str(self.number).zfill(2), self.name)

    def __repr__(self):
        return "Map(%s, '%s')" % (self.number, self.name)

class Weapon(object): pass

class Port(object):

    def __init__(self, name):
        self.name = name

class GameMode(object): pass
class Round(object): pass
class StoredPlayer(object): pass
class Alias(object): pass
class Frag(object): pass
class FlagTouch(object): pass
class FlagReturn(object): pass
class RCONAccess(object): pass
class RCONDenial(object): pass
class RCONAction(object): pass

mapper(Wad, wad_table)
mapper(Map, map_table)
mapper(Weapon, weapon_table)
mapper(Port, port_table)
mapper(GameMode, game_mode_table)
mapper(Round, round_table,
       properties={'players': relation(Alias, secondary=round_alias_table,
                                              backref='rounds')})
mapper(TeamColor, team_color_table)
mapper(StoredPlayer, player_table,
       properties={\
         'aliases': relation(Alias,
                             primaryjoin=and_(player_table.c.id == \
                                                player_alias_table.c.player_id,
                                              alias_table.c.id == \
                                                player_alias_table.c.alias_id),
                             secondary=player_alias_table,
                             backref='players', cascade='all')})
mapper(Alias, alias_table,
  properties={\
    'frags': relation(Frag,
                      primaryjoin=and_(player_table.c.id == \
                                         frag_table.c.fragger_id,
                                       frag_table.c.fragger_id != \
                                         frag_table.c.fraggee_id),
                      backref='fragger', cascade='all, delete-orphan'),
     'deaths': relation(Frag,
                        primaryjoin=player_table.c.id == \
                                      frag_table.c.fraggee_id,
                        backref='fraggee', cascade='all, delete-orphan'),
     'flag_touches': relation(FlagTouch, backref='player',
                              cascade='all, delete-orphan'),
     'flag_returns': relation(FlagReturn, backref='player',
                              cascade='all, delete-orphan'),
     'flag_picks': relation(FlagTouch,
                            primaryjoin=and_(player_table.c.id == \
                                               flag_touch_table.c.player_id,
                                             flag_touch_table.c.was_picked == \
                                               True),
                            cascade='all, delete-orphan'),
     'flag_caps': relation(FlagTouch,
                           primaryjoin=and_(player_table.c.id == \
                                              flag_touch_table.c.player_id,
                                            flag_touch_table.c.resulted_in_score == \
                                              True),
                           cascade='all, delete-orphan'),
      'flag_pick_caps': relation(FlagTouch,
                                 primaryjoin=and_(player_table.c.id == \
                                                    flag_touch_table.c.player_id,
                                                  flag_touch_table.c.was_picked == \
                                                    True,
                                                  flag_touch_table.c.resulted_in_score == \
                                                    True),
                                 cascade='all, delete-orphan'),
       'rcon_access': relation(RCONAccess, backref='player',
                               cascade='all, delete-orphan'),
       'rcon_denial': relation(RCONDenial, backref='player',
                               cascade='all, delete-orphan'),
       'rcon_action': relation(RCONAction, backref='player',
                               cascade='all, delete-orphan'),
  }
)
mapper(Frag, frag_table)
mapper(FlagTouch, flag_touch_table)
mapper(FlagReturn, flag_return_table)

