from elixir import Unicode, DateTime, Integer, Boolean, Entity, Field, \
                   OneToMany, ManyToOne, ManyToMany, using_options, \
                   using_table_options, setup_all, create_all

from sqlalchemy import UniqueConstraint, MetaData

import datetime

from ZDStack import get_engine

class TeamColor(Entity):

    color = Field(Unicode(10), primary_key=True)

    def __str__(self):
        return '<TeamColor %s>' % (self.color)

    def __repr__(self):
        return "Team('%s')" % (self.color)

class Map(Entity):

    wad = Field(Unicode(50), required=False)
    number = Field(Integer)
    name = Field(Unicode(255))
    rounds = OneToMany('Round', inverse='map')

    using_table_options(UniqueConstraint('wad', 'number', 'name'))

    def __str__(self):
        return "<Map%s: %s>" % (str(self.number).zfill(2), self.name)

    def __repr__(self):
        return "Map(%s, '%s')" % (self.number, self.name)

class Weapon(Entity):

    name = Field(Unicode(50), primary_key=True)
    is_suicide = Field(Boolean, default=False)

    def __str__(self):
        return '<Weapon %s>' % (self.name)

    def __repr__(self):
        return "Weapon('%s', %s)" % (self.name, self.is_suicide)

class Port(Entity):

    name = Field(Unicode(50), primary_key=True)
    game_modes = ManyToMany('GameMode', inverse='ports')

    def __str__(self):
        return '<Port %s>' % (self.name)

    def __repr__(self):
        return "Port('%s')" % (self.name)

class GameMode(Entity):

    name = Field(Unicode(30), primary_key=True)
    ports = ManyToMany('Port', inverse='game_modes')
    has_teams = Field(Boolean, default=False)
    rounds = OneToMany('Round', inverse='game_modes')

    def __str__(self):
        return '<GameMode %s>' % (self.name)

    def __repr__(self):
        s = "GameMode('%s', %s, %s)"
        return s % (self.name, self.port, self.has_teams)

class Round(Entity):

    game_modes = ManyToOne('GameMode', inverse='rounds')
    map = ManyToOne('Map', inverse='rounds')
    start_time = Field(DateTime, default=datetime.datetime.now)
    end_time = Field(DateTime, required=False)
    players = ManyToMany('Alias', inverse='rounds')

    def __str__(self):
        s = '<Round on %s at %s>'
        return s % (self.map, self.start_time)

    def __repr__(self):
        s = "Round(%s, %s)"
        return s % (self.map, self.start_time)

class StoredPlayer(Entity):

    name = Field(Unicode(255), primary_key=True)

    def __str__(self):
        return '<Player %s>' % (self.name)

    def __repr__(self):
        return "Player('%s')" % (self.name)

class Alias(Entity):

    name = Field(Unicode(255), index=True)
    ip_address = Field(Unicode(16), index=True)
    was_namefake = Field(Boolean, default=False, required=False)
    rounds = ManyToMany('Round', inverse='players')

    def __str__(self):
        return '<Alias %s>' % (self.name)

    def __repr__(self):
        s = "Alias('%s', '%s', %s)"
        return s % (self.name, self.ip_address, self.wad_namefake)

class Frag(Entity):

    fragger = ManyToOne('Alias')
    fraggee = ManyToOne('Alias')
    weapon = ManyToOne('Weapon')
    round = ManyToOne('Round')
    timestamp = Field(DateTime)
    fragger_was_holding_flag = Field(Boolean, default=False)
    fraggee_was_holding_flag = Field(Boolean, default=False)
    fragger_team_color = ManyToOne('TeamColor')
    fraggee_team_color = ManyToOne('TeamColor')
    red_team_holding_flag = Field(Boolean, default=False, nullable=True)
    blue_team_holding_flag = Field(Boolean, default=False, nullable=True)
    green_team_holding_flag = Field(Boolean, default=False, nullable=True)
    white_team_holding_flag = Field(Boolean, default=False, nullable=True)
    red_team_score = Field(Integer, nullable=True)
    blue_team_score = Field(Integer, nullable=True)
    green_team_score = Field(Integer, nullable=True)
    white_team_score = Field(Integer, nullable=True)

    def __str__(self):
        return '<Frag %s>' % (self.weapon)

class FlagTouch(Entity):

    player = ManyToOne('Alias')
    round = ManyToOne('Round')
    touch_time = Field(DateTime, default=datetime.datetime.now)
    loss_time = Field(DateTime, required=False)
    was_picked = Field(Boolean, default=False)
    resulted_in_score = Field(Boolean, default=False)
    player_team_color = ManyToOne('TeamColor')
    red_team_holding_flag = Field(Boolean, default=False, nullable=True)
    blue_team_holding_flag = Field(Boolean, default=False, nullable=True)
    green_team_holding_flag = Field(Boolean, default=False, nullable=True)
    white_team_holding_flag = Field(Boolean, default=False, nullable=True)
    red_team_score = Field(Integer, nullable=True)
    blue_team_score = Field(Integer, nullable=True)
    green_team_score = Field(Integer, nullable=True)
    white_team_score = Field(Integer, nullable=True)

    def __str__(self):
        return '<FlagTouch %s>' % (self.player)

class FlagReturn(Entity):

    player = ManyToOne('Alias')
    round = ManyToOne('Round')
    timestamp = Field(DateTime, default=datetime.datetime.now)
    player_was_holding_flag = Field(Boolean, default=False)
    player_team_color = ManyToOne('TeamColor')
    red_team_holding_flag = Field(Boolean, default=False, nullable=True)
    blue_team_holding_flag = Field(Boolean, default=False, nullable=True)
    green_team_holding_flag = Field(Boolean, default=False, nullable=True)
    white_team_holding_flag = Field(Boolean, default=False, nullable=True)
    red_team_score = Field(Integer, nullable=True)
    blue_team_score = Field(Integer, nullable=True)
    green_team_score = Field(Integer, nullable=True)
    white_team_score = Field(Integer, nullable=True)

    def __str__(self):
        return '<FlagReturn %s>' % (self.player)

class RCONAccess(Entity):

    player = ManyToOne('Alias')
    round = ManyToOne('Round')
    timestamp = Field(DateTime, default=datetime.datetime.now)

    def __str__(self):
        return '<RCON Access %s>' % (self.player)

class RCONDenial(Entity):

    player = ManyToOne('Alias')
    round = ManyToOne('Round')
    timestamp = Field(DateTime, default=datetime.datetime.now)

    def __str__(self):
        return '<RCON Denial %s>' % (self.player)

class RCONAction(Entity):

    player = ManyToOne('Alias')
    round = ManyToOne('Round')
    timestamp = Field(DateTime, default=datetime.datetime.now)
    action = Field(Unicode(255))

    def __str__(self):
        return '<RCON Action %s - %s>' % (self.action, self.player)

###
# Get the MetaData and bind it
###
MetaData.bind = get_engine()

###
# Setup all the mapping stuff.
###
setup_all()
###
# Should have some kind of test here that checks if the tables already exist,
# and create them if they don't.
###
create_all()

