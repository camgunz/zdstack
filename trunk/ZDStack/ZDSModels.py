import datetime

from sqlalchemy import Table, Column, ForeignKey, String, DateTime, Integer, \
                       Boolean, UniqueConstraint
from sqlalchemy.orm import relation, mapper
from sqlalchemy.ext.declarative import declarative_base

from ZDStack import get_engine, get_session_class, get_zdslog

zdslog = get_zdslog()

###
# Get the DB engine.
###
zdslog.debug("Initializing Database")
__engine = get_engine()

###
# Setup the declarative_base base class.
###
Base = declarative_base()

###
# Bind the Base's metadata.
###
zdslog.debug("Binding MetaData")
Base.metadata.bind = __engine

###
# Bind the session as well.
###
zdslog.debug("Binding Session")
get_session_class().configure(bind=__engine)

_pc = 'save-update, delete, delete-orphan'

ports_and_gamemodes = Table('ports_and_gamemodes', Base.metadata,
    Column('port_name', String(50), ForeignKey('ports.name')),
    Column('game_mode_name', String(30), ForeignKey('game_modes.name')),
    UniqueConstraint('port_name', 'game_mode_name')
)

rounds_and_aliases = Table('rounds_and_aliases', Base.metadata,
    Column('round_id', Integer, ForeignKey('rounds.id')),
    Column('alias_id', Integer, ForeignKey('aliases.id')),
    UniqueConstraint('round_id', 'alias_id')
)

aliases_table = Table('aliases', Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(255), index=True, nullable=False),
    Column('ip_address', String(16), index=True, nullable=False),
    Column('was_namefake', Boolean, default=False),
    Column('stored_player_name', String(255),
           ForeignKey('stored_players.name'), nullable=True),
    UniqueConstraint('name', 'ip_address')
)

class Alias(object):

    def __init__(self, name, ip_address):
        self.name = name
        self.ip_address = ip_address

    def __str__(self):
        return '<Alias %s>' % (self.name)

    def __repr__(self):
        s = "Alias('%s', '%s', %s)"
        return s % (self.name, self.ip_address, self.was_namefake)

class TeamColor(Base):

    __tablename__ = 'team_colors'

    color = Column(String(10), primary_key=True)
    frags = \
      relation('Frag', backref='fragger_team_color',
               cascade=_pc,
               primaryjoin='Frag.fragger_team_color_name == TeamColor.color')
    deaths = \
      relation('Frag', backref='fraggee_team_color',
               cascade=_pc,
               primaryjoin='Frag.fraggee_team_color_name == TeamColor.color')
    flag_touches = relation('FlagTouch', backref='player_team_color',
                            cascade=_pc)
    flag_returns = relation('FlagReturn', backref='player_team_color',
                            cascade=_pc)

    def __str__(self):
        return '<TeamColor %s>' % (self.color)

    def __repr__(self):
        return "Team('%s')" % (self.color)

class Map(Base):

    __tablename__ = 'maps'

    id = Column(Integer, primary_key=True)
    wad = Column(String(50))
    number = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    rounds = relation('Round', backref='map', cascade=_pc)

    UniqueConstraint(number, name)

    def __str__(self):
        return "<Map%s: %s>" % (str(self.number).zfill(2), self.name)

    def __repr__(self):
        return "Map(%s, '%s')" % (self.number, self.name)

class Weapon(Base):

    __tablename__ = 'weapons'

    name = Column(String(50), primary_key=True)
    is_suicide = Column(Boolean, default=False)
    frags = relation('Frag', backref='weapon', cascade=_pc)

    def __str__(self):
        return '<Weapon %s>' % (self.name)

    def __repr__(self):
        return "Weapon('%s', is_suicide=%s)" % (self.name, self.is_suicide)

class Port(Base):

    __tablename__ = 'ports'

    name = Column(String(50), primary_key=True)
    game_modes = relation('GameMode', secondary=ports_and_gamemodes)

    def __str__(self):
        return '<Port %s>' % (self.name)

    def __repr__(self):
        return "Port('%s')" % (self.name)

class GameMode(Base):

    __tablename__ = 'game_modes'

    name = Column(String(30), primary_key=True)
    ports = relation('Port', secondary=ports_and_gamemodes)
    has_teams = Column(Boolean, default=False, nullable=False)
    rounds = relation('Round', backref='game_mode', cascade=_pc)

    def __str__(self):
        return '<GameMode %s>' % (self.name)

    def __repr__(self):
        return "GameMode('%s', %s)" % (self.name, self.has_teams)

class Round(Base):

    __tablename__ = 'rounds'

    id = Column(Integer, primary_key=True)
    game_mode_name = Column(String(30), ForeignKey('game_modes.name'))
    map_id = Column(Integer, ForeignKey('maps.id'))
    start_time = Column(DateTime, default=datetime.datetime.now, nullable=False)
    end_time = Column(DateTime)
    players = relation(Alias, secondary=rounds_and_aliases)
    frags = relation('Frag', backref='round', cascade=_pc)
    flag_touches = relation('FlagTouch', backref='round',
                                         cascade=_pc)
    flag_returns = relation('FlagReturn', backref='round',
                                          cascade=_pc)
    rcon_accesses = relation('RCONAccess', backref='round',
                                           cascade=_pc)
    rcon_denials = relation('RCONDenial', backref='round',
                                          cascade=_pc)
    rcon_actions = relation('RCONAction', backref='round',
                                          cascade=_pc)

    def __str__(self):
        s = '<Round on %s at %s>'
        return s % (self.map, self.start_time)

    def __repr__(self):
        s = "Round(%s, %s)"
        return s % (self.map, self.start_time)

class StoredPlayer(Base):

    __tablename__ = 'stored_players'

    name = Column(String(255), primary_key=True)
    aliases = relation(Alias, backref='stored_player')

    def __str__(self):
        return '<Player %s>' % (self.name)

    def __repr__(self):
        return "Player('%s')" % (self.name)

###
# class Alias(Base):
# 
#     __tablename__ = 'aliases'
#     __table_args__ = (UniqueConstraint('name', 'ip_address'))
# 
#     id = Column(Integer, primary_key=True)
#     name = Column(String(255), index=True, nullable=False)
#     ip_address = Column(String(16), index=True, nullable=False)
#     was_namefake = Column(Boolean, default=False)
#     stored_player_name = Column(String(255), ForeignKey('stored_players.name'),
#                                 nullable=True)
#     rounds = relation('Round', secondary=rounds_and_aliases)
#     frags = relation('Frag', backref='fragger', cascade=_pc)
#     deaths = relation('Frag', backref='fraggee', cascade=_pc)
#     frags = \
#       relation('Frag', backref='fragger',
#                cascade=_pc,
#                primaryjoin='Frag.fragger_id == Alias.id')
#     deaths = \
#       relation('Frag', backref='fraggee',
#                cascade=_pc,
#                primaryjoin='Frag.fraggee_id == Alias.id')
#     flag_touches = relation('FlagTouch', backref='player',
#                             cascade=_pc)
#     flag_returns = relation('FlagReturn', backref='player',
#                             cascade=_pc)
#     rcon_accesses = relation('RCONAccess', backref='player',
#                              cascade=_pc)
#     rcon_denials = relation('RCONDenial', backref='player',
#                             cascade=_pc)
#     rcon_actions = relation('RCONAction', backref='player',
#                             cascade=_pc)
# 
#     def __str__(self):
#         return '<Alias %s>' % (self.name)
# 
#     def __repr__(self):
#         s = "Alias('%s', '%s', %s)"
#         return s % (self.name, self.ip_address, self.was_namefake)
###

class Frag(Base):

    __tablename__ = 'frags'

    id = Column(Integer, primary_key=True)
    fragger_id = Column(Integer, ForeignKey('aliases.id'))
    fraggee_id = Column(Integer, ForeignKey('aliases.id'))
    weapon_name = Column(String(50), ForeignKey('weapons.name'))
    round_id = Column(Integer, ForeignKey('rounds.id'))
    timestamp = Column(DateTime, nullable=False)
    fragger_was_holding_flag = Column(Boolean, default=False)
    fraggee_was_holding_flag = Column(Boolean, default=False)
    fragger_team_color_name = Column(String(10), ForeignKey('team_colors.color'))
    fraggee_team_color_name = Column(String(10), ForeignKey('team_colors.color'))
    red_team_holding_flag = Column(Boolean, default=False)
    blue_team_holding_flag = Column(Boolean, default=False)
    green_team_holding_flag = Column(Boolean, default=False)
    white_team_holding_flag = Column(Boolean, default=False)
    red_team_score = Column(Integer)
    blue_team_score = Column(Integer)
    green_team_score = Column(Integer)
    white_team_score = Column(Integer)

    def __str__(self):
        return '<Frag %s>' % (self.weapon)

class FlagTouch(Base):

    __tablename__ = 'flag_touches'

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('aliases.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))
    touch_time = Column(DateTime, default=datetime.datetime.now, nullable=False)
    loss_time = Column(DateTime)
    was_picked = Column(Boolean, default=False, nullable=False)
    resulted_in_score = Column(Boolean, default=False)
    player_team_color_name = Column(String(10), ForeignKey('team_colors.color'))
    red_team_holding_flag = Column(Boolean, default=False)
    blue_team_holding_flag = Column(Boolean, default=False)
    green_team_holding_flag = Column(Boolean, default=False)
    white_team_holding_flag = Column(Boolean, default=False)
    red_team_score = Column(Integer)
    blue_team_score = Column(Integer)
    green_team_score = Column(Integer)
    white_team_score = Column(Integer)

    def __str__(self):
        return '<FlagTouch %s>' % (self.player)

class FlagReturn(Base):

    __tablename__ = 'flag_returns'

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('aliases.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))
    timestamp = Column(DateTime, default=datetime.datetime.now)
    player_was_holding_flag = Column(Boolean, default=False)
    player_team_color_name = Column(String(10), ForeignKey('team_colors.color'))
    red_team_holding_flag = Column(Boolean, default=False)
    blue_team_holding_flag = Column(Boolean, default=False)
    green_team_holding_flag = Column(Boolean, default=False)
    white_team_holding_flag = Column(Boolean, default=False)
    red_team_score = Column(Integer)
    blue_team_score = Column(Integer)
    green_team_score = Column(Integer)
    white_team_score = Column(Integer)

    def __str__(self):
        return '<FlagReturn %s>' % (self.player)

class RCONAccess(Base):

    __tablename__ = 'rcon_accesses'

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('aliases.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))
    timestamp = Column(DateTime, default=datetime.datetime.now, nullable=False)

    def __str__(self):
        return '<RCON Access %s>' % (self.player)

class RCONDenial(Base):

    __tablename__ = 'rcon_denials'

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('aliases.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))
    timestamp = Column(DateTime, default=datetime.datetime.now, nullable=False)

    def __str__(self):
        return '<RCON Denial %s>' % (self.player)

class RCONAction(Base):

    __tablename__ = 'rcon_actions'

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('aliases.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))
    timestamp = Column(DateTime, default=datetime.datetime.now, nullable=False)
    action = Column(String(255), nullable=False)

    def __str__(self):
        return '<RCON Action %s - %s>' % (self.action, self.player)

mapper(Alias, aliases_table, properties={
    'rounds': relation(Round, secondary=rounds_and_aliases),
    'frags': relation(Frag, backref='fragger', cascade=_pc),
    'deaths': relation(Frag, backref='fraggee', cascade=_pc),
    'frags': relation(Frag, backref='fragger', cascade=_pc,
                      primaryjoin=Frag.fragger_id == aliases_table.c.id),
    'deaths': relation(Frag, backref='fraggee', cascade=_pc,
                       primaryjoin=Frag.fraggee_id == aliases_table.c.id),
    'flag_touches': relation(FlagTouch, backref='player', cascade=_pc),
    'flag_returns': relation(FlagReturn, backref='player', cascade=_pc),
    'rcon_accesses': relation(RCONAccess, backref='player', cascade=_pc),
    'rcon_denials': relation(RCONDenial, backref='player', cascade=_pc),
    'rcon_actions': relation(RCONAction, backref='player', cascade=_pc)
})

zdslog.debug("Creating tables")
Base.metadata.create_all(__engine)

