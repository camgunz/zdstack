import sqlalchemy

CONN_STRING = ''

ENGINE = sqlalchemy.create_engine(CONN_STRING)

METADATA = sqlalchemy.MetaData()

ZSERVS_TABLE = \
    Table('zservs', METADATA,
          sqlalchemy.Column('id', Integer, primary_key=True),
          sqlalchemy.Column('name', String(100), unique=True),
          sqlalchemy.Column('map_name', String(50)),
          sqlalchemy.Column('map_number', Integer))

MAPS_TABLE = \
    Table('maps', METADATA,
          sqlalchemy.Column(

TEAMS_TABLE = \
    Table('teams', METADATA,
          sqlalchemy.Column('id', Integer, primary_key=True),

PLAYERS_TABLE = \
    Table('players', METADATA,
          sqlalchemy.Column('id', Integer, primary_key=True),
          sqlalchemy.Column('zserv_id', Integer, ForeignKey('zservs.id'))
          sqlalchemy.Column('name', String(15)),
          sqlalchemy.Column('team', Integer)
          sqlalchemy.Column('id', Integer, primary_key=True))

                    

def sql_export(event, zserv):
    
