from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, \
                       MetaData, UniqueConstraint, ForeignKey

from ZDStack import get_engine, get_metadata

metadata = get_metadata()

__all__ = ['info_table', 'wad_table', 'map_table', 'weapon_table',
           'port_table', 'game_mode_table', 'round_table', 'team_table',
           'player_table', 'alias_table', 'player_address_table',
           'round_alias_table', 'player_alias_table', 'frag_table',
           'flag_touch_table', 'flag_return_table']

info_table = Table('info', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('schema_version', Integer, unique=True)
)

wad_table = Table('wads', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('name', String(50), unique=True)
)

map_table = Table('maps', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('wad_id', ForeignKey('wads.id')),
    Column('number', Integer),
    Column('name', String(255)),
    UniqueConstraint(['wad_id', 'number'])
)

weapon_table = Table('weapons', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('name', String(50), unique=True),
    Column('is_suicide', Boolean)
)

port_table = Table('ports', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('name', String(50))
)

game_mode_table = Table('game_modes', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('port_id', ForeignKey('ports.id')),
    Column('name', String(30)),
    Column('number_of_teams', Integer, default=0)
)

round_table = Table('rounds', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('game_mode', ForeignKey('game_modes.id')),
    Column('map', ForeignKey('maps.id')),
    Column('start_time', DateTime),
    Column('end_time', DateTime)
)

team_table = Table('teams', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('color', String(10), unique=True)
)

player_table = Table('players', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('name', String(255), unique=True, index=True)
)

alias_table = Table('aliases', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('name', String(255), index=True)
    Column('player_id', ForeignKey('players.id'), nullable=True)
)

player_address_table = Table('player_addresses', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('player_id', ForeignKey('aliases.id'), nullable=True, index=True),
    Column('ip_address', String(50), index=True),
    Column('was_namefake', Boolean, default=False)
)

player_alias_table = Table('player_aliases', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('player_id', ForeignKey('players.id')),
    Column('alias_id', ForeignKey('alias.id'))
)

round_alias_table = Table('round_aliases', metadata,
    Column('round_id', ForeignKey('rounds.id')),
    Column('player_id', ForeignKey('aliases.id'))
)

frag_table = Table('frags', metadata,
  Column('id', Integer, primary_key=True, autoincrement=True),
  Column('fragger_id', ForeignKey('aliases.id'), index=True),
  Column('fraggee_id', ForeignKey('aliases.id'), index=True),
  Column('weapon_id', ForeignKey('weapons.id'), index=True),
  Column('round_id', ForeignKey('rounds.id'), index=True),
  Column('timestamp', DateTime),
  Column('fragger_was_holding_flag', Boolean, default=False),
  Column('fraggee_was_holding_flag', Boolean, default=False),
  Column('fragger_team_id', ForeignKey('teams.id'), nullable=True, index=True),
  Column('fraggee_team_id', ForeignKey('teams.id'), nullable=True, index=True),
  Column('red_team_holding_flag', Boolean, default=False, nullable=True),
  Column('blue_team_holding_flag', Boolean, default=False, nullable=True),
  Column('green_team_holding_flag', Boolean, default=False, nullable=True),
  Column('white_team_holding_flag', Boolean, default=False, nullable=True),
  Column('red_team_score', Integer, nullable=True),
  Column('blue_team_score', Integer, nullable=True),
  Column('green_team_score', Integer, nullable=True),
  Column('white_team_score', Integer, nullable=True)
)

flag_touch_table = Table('flag_touches', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('player_id', ForeignKey('aliases.id'), index=True),
    Column('round_id', ForeignKey('rounds.id'), index=True),
    Column('touch_time', DateTime),
    Column('loss_time', DateTime, nullable=True),
    Column('was_picked', Boolean, default=False),
    Column('resulted_in_score', Boolean, default=False),
    Column('player_team_id', ForeignKey('teams.id'), nullable=True, index=True),
    Column('red_team_score', Integer, nullable=True),
    Column('blue_team_score', Integer, nullable=True),
    Column('green_team_score', Integer, nullable=True),
    Column('white_team_score', Integer, nullable=True)
)

flag_return_table = Table('flag_returns', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('player_id', ForeignKey('aliases.id'), index=True),
    Column('round_id', ForeignKey('rounds.id'), index=True),
    Column('timestamp', DateTime),
    Column('player_was_holding_flag', Boolean, default=False),
    Column('red_team_holding_flag', Boolean, default=False, nullable=True),
    Column('blue_team_holding_flag', Boolean, default=False, nullable=True),
    Column('green_team_holding_flag', Boolean, default=False, nullable=True),
    Column('white_team_holding_flag', Boolean, default=False, nullable=True),
    Column('red_team_score', Integer, nullable=True),
    Column('blue_team_score', Integer, nullable=True),
    Column('green_team_score', Integer, nullable=True),
    Column('white_team_score', Integer, nullable=True)
)

metadata.create_all() # will this raise exceptions if tables exist?

