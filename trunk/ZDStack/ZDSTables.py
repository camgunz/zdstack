import datetime

from sqlalchemy import Table, Column, ForeignKey, Index, String, DateTime, \
                       Integer, Boolean, Unicode, UniqueConstraint, MetaData

from ZDStack import get_engine, get_metadata, get_zdslog

zdslog = get_zdslog()

###
# Get the DB engine.
###
zdslog.debug("Initializing Database")
__engine = get_engine()
__metadata = get_metadata()

ports_and_gamemodes = Table('ports_and_gamemodes', __metadata,
    Column('port_name', String(50), ForeignKey('ports.name')),
    Column('game_mode_name', String(30), ForeignKey('game_modes.name')),
    UniqueConstraint('port_name', 'game_mode_name')
)

rounds_and_aliases = Table('rounds_and_aliases', __metadata,
    Column('id', Integer, primary_key=True),
    Column('round_id', Integer, ForeignKey('rounds.id')),
    Column('alias_id', Integer, ForeignKey('aliases.id')),
    UniqueConstraint('round_id', 'alias_id')
)

aliases_table = Table('aliases', __metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(255), index=True, nullable=False),
    Column('ip_address', String(16), index=True, nullable=False),
    Column('was_namefake', Boolean, default=False),
    Column('stored_player_name', Unicode(255),
           ForeignKey('stored_players.name'), nullable=True),
    UniqueConstraint('name', 'ip_address')
)

team_colors_table = Table('team_colors', __metadata,
    Column('color', String(10), primary_key=True)
)

wads_table = Table('wads', __metadata,
    Column('name', String(20), primary_key=True)
)

maps_table = Table('maps', __metadata,
    Column('id', Integer, primary_key=True),
    Column('wad_name', String(20), ForeignKey('wads.name')),
    Column('number', Integer, nullable=False),
    Column('name', String(255), nullable=False),
    UniqueConstraint('number', 'name')
)

weapons_table = Table('weapons', __metadata,
    Column('name', String(50), primary_key=True),
    Column('is_suicide', Boolean, default=False)
)

ports_table = Table('ports', __metadata,
    Column('name', String(50), primary_key=True)
)

game_modes_table = Table('game_modes', __metadata,
    Column('name', String(30), primary_key=True),
    Column('has_teams', Boolean, default=False, nullable=False)
)

rounds_table = Table('rounds', __metadata,
    Column('id', Integer, primary_key=True),
    Column('game_mode_name', String(30), ForeignKey('game_modes.name')),
    Column('map_id', Integer, ForeignKey('maps.id')),
    Column('start_time', DateTime, default=datetime.datetime.now,
           nullable=False),
    Column('end_time', DateTime)
)

stored_players_table = Table('stored_players', __metadata,
    Column('name', Unicode(255), primary_key=True)
)

frags_table = Table('frags', __metadata,
 Column('id', Integer, primary_key=True),
 Column('fragger_id', Integer, ForeignKey('aliases.id'), index=True),
 Column('fraggee_id', Integer, ForeignKey('aliases.id'), index=True),
 Column('weapon_name', String(50), ForeignKey('weapons.name')),
 Column('round_id', Integer, ForeignKey('rounds.id'), index=True),
 Column('timestamp', DateTime, nullable=False),
 Column('fragger_was_holding_flag', Boolean, default=False),
 Column('fraggee_was_holding_flag', Boolean, default=False),
 Column('fragger_team_color_name', String(10), ForeignKey('team_colors.color'),
        index=True),
 Column('fraggee_team_color_name', String(10), ForeignKey('team_colors.color'),
        index=True),
 Column('red_team_holding_flag', Boolean, default=False),
 Column('blue_team_holding_flag', Boolean, default=False),
 Column('green_team_holding_flag', Boolean, default=False),
 Column('white_team_holding_flag', Boolean, default=False),
 Column('red_team_score', Integer),
 Column('blue_team_score', Integer),
 Column('green_team_score', Integer),
 Column('white_team_score', Integer)
)

flag_touches_table = Table('flag_touches', __metadata,
 Column('id', Integer, primary_key=True),
 Column('player_id', Integer, ForeignKey('aliases.id'), index=True),
 Column('round_id', Integer, ForeignKey('rounds.id'), index=True),
 Column('touch_time', DateTime, default=datetime.datetime.now, nullable=False),
 Column('loss_time', DateTime),
 Column('was_picked', Boolean, default=False, nullable=False),
 Column('resulted_in_score', Boolean, default=False),
 Column('player_team_color_name', String(10), ForeignKey('team_colors.color'),
        index=True),
 Column('red_team_holding_flag', Boolean, default=False),
 Column('blue_team_holding_flag', Boolean, default=False),
 Column('green_team_holding_flag', Boolean, default=False),
 Column('white_team_holding_flag', Boolean, default=False),
 Column('red_team_score', Integer),
 Column('blue_team_score', Integer),
 Column('green_team_score', Integer),
 Column('white_team_score', Integer)
)

flag_returns_table = Table('flag_returns', __metadata,
 Column('id', Integer, primary_key=True),
 Column('player_id', Integer, ForeignKey('aliases.id'), index=True),
 Column('round_id', Integer, ForeignKey('rounds.id'), index=True),
 Column('timestamp', DateTime, default=datetime.datetime.now),
 Column('player_was_holding_flag', Boolean, default=False),
 Column('player_team_color_name', String(10), ForeignKey('team_colors.color'),
        index=True),
 Column('red_team_holding_flag', Boolean, default=False),
 Column('blue_team_holding_flag', Boolean, default=False),
 Column('green_team_holding_flag', Boolean, default=False),
 Column('white_team_holding_flag', Boolean, default=False),
 Column('red_team_score', Integer),
 Column('blue_team_score', Integer),
 Column('green_team_score', Integer),
 Column('white_team_score', Integer)
)

rcon_accesses_table = Table('rcon_accesses', __metadata,
    Column('id', Integer, primary_key=True),
    Column('player_id', Integer, ForeignKey('aliases.id')),
    Column('round_id', Integer, ForeignKey('rounds.id')),
    Column('timestamp', DateTime, default=datetime.datetime.now)
)

rcon_actions_table = Table('rcon_actions', __metadata,
    Column('id', Integer, primary_key=True),
    Column('player_id', Integer, ForeignKey('aliases.id')),
    Column('round_id', Integer, ForeignKey('rounds.id')),
    Column('timestamp', DateTime, default=datetime.datetime.now),
    Column('action', String(255))
)

rcon_denials_table = Table('rcon_denials', __metadata,
    Column('id', Integer, primary_key=True),
    Column('player_id', Integer, ForeignKey('aliases.id')),
    Column('round_id', Integer, ForeignKey('rounds.id')),
    Column('timestamp', DateTime, default=datetime.datetime.now)
)

