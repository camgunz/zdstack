import datetime

from sqlalchemy import Table, Column, ForeignKey, Index, String, DateTime, \
                       Integer, Boolean, UniqueConstraint
from sqlalchemy.orm import relation, mapper
from sqlalchemy.ext.declarative import declarative_base

from ZDStack import get_engine, get_session_class, get_zdslog

zdslog = get_zdslog()

###
# TODO: Create table indexes, which look like:
#
# Index('myindex', mytable.c.col5, mytable.c.col6, unique=True)
#
###

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

    """Alias represents a player's alias.

    .. attribute:: name
        A string representing the alias' name
    .. attribute:: ip_address
        A string representing the alias' IP address

    There is no way for ZDStack to determine player identity
    completely on its own; an administrator must setup mappings between
    StoredPlayers and Aliases.  However, player names and address must
    be stored, so we assume that everything is an Alias and store it as
    such.

    """

    def __init__(self, name, ip_address):
        self.name = name
        self.ip_address = ip_address

    def __str__(self):
        return '<Alias %s>' % (self.name)

    def __repr__(self):
        s = "Alias('%s', '%s')"
        return s % (self.name, self.ip_address)

class TeamColor(Base):

    """TeamColor represents a team's color.

    .. attribute:: color
        A string representing the team's color

    .. attribute:: frags
        A list of this team color's Frags

    .. attribute:: deaths
        A list of this team color's Deaths (Frags)

    .. attribute:: flag_touches
        A list of this team color's FlagTouches

    .. attribute:: flag_returns
        A list of this team color's FlagReturns

    Teams can be much more than just colors, for instance, it's
    possible for an IDL 'team' to play different rounds as different
    using different 'team colors'.  So we simply store the team's color
    and require the administrator to create their own mapping between
    whatever they think a 'team' is, and that team's color in the
    round.

    """

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

    """Map represents a map in a WAD.

    .. attribute:: id
        The database ID of this Map

    .. attribute:: wad
        A string representing the name of the containing WAD

    .. attribute:: number
        An int representing the number of this Map in the containing
        WAD

    .. attribute:: name
        A string representing the name of this Map

    .. attribute:: rounds
        A list of Rounds played on this Map

    """

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

    """Weapon represents something that kills players.

    .. attribute:: name
        A string representing the name of the Weapon
    .. attribute:: is_suicide
        A boolean, whether or not the Weapon is a suicide
    .. attribute: frags
        A list of this Weapon's Frags

    """

    __tablename__ = 'weapons'

    name = Column(String(50), primary_key=True)
    is_suicide = Column(Boolean, default=False)
    frags = relation('Frag', backref='weapon', cascade=_pc)

    def __str__(self):
        return '<Weapon %s>' % (self.name)

    def __repr__(self):
        return "Weapon('%s', is_suicide=%s)" % (self.name, self.is_suicide)

class Port(Base):

    """Port represents a Doom source port.

    .. attribute:: name
        A string representing the name of this Port

    .. attribute:: game_modes
        A list of this Port's GameModes

    """

    __tablename__ = 'ports'

    name = Column(String(50), primary_key=True)
    game_modes = relation('GameMode', secondary=ports_and_gamemodes)

    def __str__(self):
        return '<Port %s>' % (self.name)

    def __repr__(self):
        return "Port('%s')" % (self.name)

class GameMode(Base):

    """GameMode represents a game's mode, i.e. TeamDM, CTF, etc.

    .. attribute:: name
        A string representing this GameMode's name

    .. attribute:: ports
        This GameMode's Port

    .. attribute:: has_teams
        A boolean, whether or not this GameMode employs teams

    .. attribute:: rounds
        A list of Rounds played using this GameMode

    """

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

    """A Round represents a single round of play.

    .. attribute:: id
        The database ID of this Round

    .. attribute:: game_mode_name
        The name of this Round's GameMode

    .. attribute:: map_id
        The ID of this Round's Map

    .. attribute:: start_time
        A datetime representing the start of this Round

    .. attribute: end_time
        A datetime representing the end of this Round

    .. attribute:: players
        A list of this Round's Aliases

    .. attribute:: frags
        A list of this Round's Frags

    .. attribute:: flag_touches
        A list of this Round's FlagTouches

    .. attribute:: flag_returns
        A list of this Round's FlagReturns

    .. attribute:: rcon_accesses
        A list of this Round's RCONAccesses

    .. attribute:: rcon_denials
        A list of this Round's RCONDenials

    .. attribute:: rcon_actions
        A list of this Round's RCONActions

    """

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

    """Represents a player.

    .. attribute:: name
        A string representing the name of this StoredPlayer

    .. attribute:: aliases
        A list of this StoredPlayer's Aliases

    """

    __tablename__ = 'stored_players'

    name = Column(String(255), primary_key=True)
    aliases = relation(Alias, backref='stored_player')

    def __str__(self):
        return '<Player %s>' % (self.name)

    def __repr__(self):
        return "Player('%s')" % (self.name)

class Frag(Base):

    """Represents a frag.

    .. attribute:: id
        The database ID of this Frag

    .. attribute:: fragger_id
        The database ID of this Frag's fragger (Alias)

    .. attribute:: fraggee_id
        The database ID of this Frag's fraggee (Alias)

    .. attribute:: weapon_name
        The name of this Frag's Weapon

    .. attribute:: round_id
        The database ID of this Frag's Round

    .. attribute:: timestamp
        A datetime representing the time at which this Frag occurred

    .. attribute:: fragger_was_holding_flag
        A boolean, whether or not the fragger was holding a flag

    .. attribute:: fraggee_was_holding_flag
        A boolean, whether or not the fraggee was holding a flag

    .. attribute:: fragger_team_color_name
        The name of fragger's TeamColor

    .. attribute:: fraggee_team_color_name
        The name of fraggee's TeamColor

    .. attribute:: red_team_holding_flag
        A boolean whether or not the red team was holding the flag

    .. attribute:: blue_team_holding_flag
        A boolean whether or not the blue team was holding the flag

    .. attribute:: green_team_holding_flag
        A boolean whether or not the green team was holding the flag

    .. attribute:: white_team_holding_flag
        A boolean whether or not the white team was holding the flag

    .. attribute:: red_team_score
        An int representing the red team's score

    .. attribute:: blue_team_score
        An int representing the blue team's score

    .. attribute:: green_team_score
        An int representing the green team's score

    .. attribute:: white_team_score
        An int representing the white team's score

    """

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

    """Represents a flag touch.

    .. attribute:: id
        The database ID of this FlagTouch

    .. attribute:: player_id
        The database ID of this FlagTouch's player (Alias)

    .. attribute:: round_id
        The database ID of this FlagTouch's Round

    .. attribute:: touch_time
        A datetime representing the time at which this FlagTouch
        began

    .. attribute:: loss_time
        A datetime representing the time at which this FlagTouch
        ended

    .. attribute:: was_picked
        A boolean, whether or not the flag was picked up (as opposed to
        taken from an enemy team's flag stand)

    .. attribute:: resulted_in_score
        A boolean, whether or not this FlagTouch ultimately resulted in
        a capture

    .. attribute:: player_team_color_name
        The name of player's TeamColor

    .. attribute:: red_team_holding_flag
        A boolean whether or not the red team was holding the flag

    .. attribute:: blue_team_holding_flag
        A boolean whether or not the blue team was holding the flag

    .. attribute:: green_team_holding_flag
        A boolean whether or not the green team was holding the flag

    .. attribute:: white_team_holding_flag
        A boolean whether or not the white team was holding the flag

    .. attribute:: red_team_score
        An int representing the red team's score

    .. attribute:: blue_team_score
        An int representing the blue team's score

    .. attribute:: green_team_score
        An int representing the green team's score

    .. attribute:: white_team_score
        An int representing the white team's score

    """

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

    """Represents a flag return.

    .. attribute:: id
        The database ID of this FlagReturn

    .. attribute:: player_id
        The database ID of this FlagReturn's player (Alias)

    .. attribute:: round_id
        The database ID of this FlagReturn's Round

    .. attribute:: timestamp
        A datetime representing the time at which this FlagReturn
        occurred

    .. attribute:: player_was_holding_flag
        A boolean, whether or not the returning player was holding a
        flag

    .. attribute:: player_team_color_name
        The name of player's TeamColor

    .. attribute:: red_team_holding_flag
        A boolean whether or not the red team was holding the flag

    .. attribute:: blue_team_holding_flag
        A boolean whether or not the blue team was holding the flag

    .. attribute:: green_team_holding_flag
        A boolean whether or not the green team was holding the flag

    .. attribute:: white_team_holding_flag
        A boolean whether or not the white team was holding the flag

    .. attribute:: red_team_score
        An int representing the red team's score

    .. attribute:: blue_team_score
        An int representing the blue team's score

    .. attribute:: green_team_score
        An int representing the green team's score

    .. attribute:: white_team_score
        An int representing the white team's score

    """

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

    """Represents an RCON access.

    .. attribute:: id
        The database ID of this RCON access

    .. attribute:: player_id
        The database ID of this RCON access's player (Alias)

    .. attribute:: round_id
        The database ID of this RCON access's Round

    .. attribute:: timestamp
        A datetime representing the time at which this RCON access
        occurred

    """

    __tablename__ = 'rcon_accesses'

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('aliases.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))
    timestamp = Column(DateTime, default=datetime.datetime.now, nullable=False)

    def __str__(self):
        return '<RCON Access %s>' % (self.player)

class RCONDenial(Base):

    """Represents an RCON denial.

    .. attribute:: id
        The database ID of this RCON denial

    .. attribute:: player_id
        The database ID of this RCON denial's player (Alias)

    .. attribute:: round_id
        The database ID of this RCON denial's Round

    .. attribute:: timestamp
        A datetime representing the time at which this RCON denial
        occurred

    """

    __tablename__ = 'rcon_denials'

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('aliases.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))
    timestamp = Column(DateTime, default=datetime.datetime.now, nullable=False)

    def __str__(self):
        return '<RCON Denial %s>' % (self.player)

class RCONAction(Base):

    """Represents an RCON action.

    .. attribute:: id
        The database ID of this RCON action

    .. attribute:: player_id
        The database ID of this RCON action's player (Alias)

    .. attribute:: round_id
        The database ID of this RCON action's Round

    .. attribute:: timestamp
        A datetime representing the time at which this RCON action
        occurred

    """

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

