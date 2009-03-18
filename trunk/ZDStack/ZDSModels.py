from sqlalchemy import relation, and_
from sqlalchemy.orm import mapper

from ZDStack import get_engine
from ZDStack.ZDSTables import *

class Wad(object): pass
class Map(object): pass
class Weapon(object): pass
class Port(object): pass
class GameMode(object): pass
class Round(object): pass
class Team(object): pass
class Player(object): pass
class PlayerIP(object): pass
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
                                       'players': relation(Player, secondary=round_player_table, backref='rounds')})
mapper(Team, team_table, properties={'frags': relation(Frag, backref='team'),
                                     'flag_touches': relation(FlagTouch, backref='team'),
                                     'flag_returns': relation(FlagReturn, backref='team')})
mapper(Player, player_table, properties={'ip_addresses': relation(PlayerIP, backref='player',
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
mapper(PlayerIP, player_ip_table)
mapper(Frag, frag_table)
mapper(FlagTouch, flag_touch_table)
mapper(FlagReturn, flag_return_table)

