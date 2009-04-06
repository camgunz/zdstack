from __future__ import with_statement

from elixir import String, DateTime, Integer, Boolean, Entity, Field, \
                   OneToMany, ManyToOne, ManyToMany, using_options, \
                   using_table_options, setup_all, create_all, session

from sqlalchemy import UniqueConstraint, MetaData
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exceptions import IntegrityError

import datetime

from ZDStack import get_engine, get_db_lock

class TeamColor(Entity):

    color = Field(String(10), primary_key=True)
    frags = OneToMany('Frag', inverse='fragger_team_color')
    deaths = OneToMany('Frag', inverse='fraggee_team_color')
    flag_touches = OneToMany('FlagTouch', inverse='player_team_color')
    flag_returns = OneToMany('FlagReturn', inverse='player_team_color')

    def __str__(self):
        return '<TeamColor %s>' % (self.color)

    def __repr__(self):
        return "Team('%s')" % (self.color)

class Map(Entity):

    wad = Field(String(50), required=False)
    number = Field(Integer)
    name = Field(String(255))
    rounds = OneToMany('Round', inverse='map')

    using_table_options(UniqueConstraint('number', 'name'))

    def __str__(self):
        return "<Map%s: %s>" % (str(self.number).zfill(2), self.name)

    def __repr__(self):
        return "Map(%s, '%s')" % (self.number, self.name)

class Weapon(Entity):

    name = Field(String(50), primary_key=True)
    is_suicide = Field(Boolean, default=False)
    frags = OneToMany('Frag', inverse='weapon')

    def __str__(self):
        return '<Weapon %s>' % (self.name)

    def __repr__(self):
        return "Weapon('%s', %s)" % (self.name, self.is_suicide)

class Port(Entity):

    name = Field(String(50), primary_key=True)
    game_modes = ManyToMany('GameMode', inverse='ports')

    def __str__(self):
        return '<Port %s>' % (self.name)

    def __repr__(self):
        return "Port('%s')" % (self.name)

class GameMode(Entity):

    name = Field(String(30), primary_key=True)
    ports = ManyToMany('Port', inverse='game_modes')
    has_teams = Field(Boolean, default=False)
    rounds = OneToMany('Round', inverse='game_modes')

    def __str__(self):
        return '<GameMode %s>' % (self.name)

    def __repr__(self):
        return "GameMode('%s', %s)" % (self.name, self.has_teams)

class Round(Entity):

    game_modes = ManyToOne('GameMode', inverse='rounds')
    map = ManyToOne('Map', inverse='rounds')
    start_time = Field(DateTime, default=datetime.datetime.now)
    end_time = Field(DateTime, required=False)
    players = ManyToMany('Alias', inverse='rounds')
    frags = OneToMany('Frag', inverse='round')
    flag_touches = OneToMany('FlagTouch', inverse='round')
    flag_returns = OneToMany('FlagReturn', inverse='round')
    rcon_accesses = OneToMany('RCONAccess', inverse='round')
    rcon_denials = OneToMany('RCONDenial', inverse='round')
    rcon_actions = OneToMany('RCONAction', inverse='round')

    def __str__(self):
        s = '<Round on %s at %s>'
        return s % (self.map, self.start_time)

    def __repr__(self):
        s = "Round(%s, %s)"
        return s % (self.map, self.start_time)

class StoredPlayer(Entity):

    name = Field(String(255), primary_key=True)

    def __str__(self):
        return '<Player %s>' % (self.name)

    def __repr__(self):
        return "Player('%s')" % (self.name)

class Alias(Entity):

    name = Field(String(255), index=True)
    ip_address = Field(String(16), index=True)
    was_namefake = Field(Boolean, default=False, required=False)
    rounds = ManyToMany('Round', inverse='players')
    frags = OneToMany('Frag', inverse='fragger')
    deaths = OneToMany('Frag', inverse='fraggee')
    flag_touches = OneToMany('FlagTouch', inverse='player')
    flag_returns = OneToMany('FlagReturn', inverse='player')
    rcon_accesses = OneToMany('RCONAccess', inverse='player')
    rcon_denials = OneToMany('RCONDenial', inverse='player')
    rcon_actions = OneToMany('RCONAction', inverse='player')

    def __str__(self):
        return '<Alias %s>' % (self.name)

    def __repr__(self):
        s = "Alias('%s', '%s', %s)"
        return s % (self.name, self.ip_address, self.wad_namefake)

class Frag(Entity):

    fragger = ManyToOne('Alias', inverse='frags')
    fraggee = ManyToOne('Alias', inverse='deaths')
    weapon = ManyToOne('Weapon', inverse='frags')
    round = ManyToOne('Round', inverse='frags')
    timestamp = Field(DateTime)
    fragger_was_holding_flag = Field(Boolean, default=False)
    fraggee_was_holding_flag = Field(Boolean, default=False)
    fragger_team_color = ManyToOne('TeamColor', inverse='frags')
    fraggee_team_color = ManyToOne('TeamColor', inverse='deaths')
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

    player = ManyToOne('Alias', inverse='flag_touches')
    round = ManyToOne('Round', inverse='flag_touches')
    touch_time = Field(DateTime, default=datetime.datetime.now)
    loss_time = Field(DateTime, required=False)
    was_picked = Field(Boolean, default=False)
    resulted_in_score = Field(Boolean, default=False)
    player_team_color = ManyToOne('TeamColor', inverse='flag_touches')
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

    player = ManyToOne('Alias', inverse='flag_returns')
    round = ManyToOne('Round', inverse='flag_returns')
    timestamp = Field(DateTime, default=datetime.datetime.now)
    player_was_holding_flag = Field(Boolean, default=False)
    player_team_color = ManyToOne('TeamColor', inverse='flag_returns')
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

    player = ManyToOne('Alias', inverse='rcon_accesses')
    round = ManyToOne('Round', inverse='rcon_accesses')
    timestamp = Field(DateTime, default=datetime.datetime.now)

    def __str__(self):
        return '<RCON Access %s>' % (self.player)

class RCONDenial(Entity):

    player = ManyToOne('Alias', inverse='rcon_denials')
    round = ManyToOne('Round', inverse='rcon_denials')
    timestamp = Field(DateTime, default=datetime.datetime.now)

    def __str__(self):
        return '<RCON Denial %s>' % (self.player)

class RCONAction(Entity):

    player = ManyToOne('Alias', inverse='rcon_actions')
    round = ManyToOne('Round', inverse='rcon_actions')
    timestamp = Field(DateTime, default=datetime.datetime.now)
    action = Field(String(255))

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

###
# What follows is ridiculous, and I can't imagine this is what you are
# actually supposed to do.  But FUCK if I can't figure out how to get
# SQLAlchemy to think for itself and not INSERT rows that already exist.
# Goddamn.
#
# It's very simple:
#
#   Some stuff I want saved and some stuff I don't, so I can't use autoflush,
#     autocommit, or save_on_init.  I can see how that's handy though.
#   I'd rather not manually do a query to see if the object I'm about to create
#     has ever, in the entire goddamn history of the database, been
#     instantiated before.
#   When I do decide I want to save things, I'd rather not manually check the
#     session AND the database if it has ever been saved before.
#   I don't want to subclass things or create MixIn junk or find random
#     configuration "DSL" methods with obscure, random names to do this.
#
# OK, rant over.  Shit.
###

def get_weapon(name, is_suicide):
    q = session.query(Weapon).filter_by(name=name, is_suicide=is_suicide)
    try:
        return q.one()
    except NoResultFound:
        with get_db_lock():
            out = Weapon(name=name, is_suicide=is_suicide)
            try:
                session.add(out)
                session.commit()
            except IntegrityError:
                session.rollback()
                pass
        return get_weapon(name, is_suicide)

def get_alias(name, ip_address, round=None):
    q = session.query(Alias).filter_by(name=name, ip_address=ip_address)
    out = q.first()
    if out:
        return out
    elif round:
        with get_db_lock():
            out = Alias(name=name, ip_address=ip_address, round=round)
            try:
                session.add(out)
                session.commit()
            except IntegrityError:
                session.rollback()
                pass
        return get_alias(name, ip_address, round)
    else:
        return None

def get_team_color(color):
    q = session.query(TeamColor).filter_by(color=color)
    try:
        return q.one()
    except NoResultFound:
        with get_db_lock():
            out = TeamColor(color=color)
            try:
                session.add(out)
                session.commit()
            except IntegrityError:
                session.rollback()
                pass
        return get_team_color(color)

def get_port(name):
    q = session.query(Port).filter_by(name=name)
    try:
        return q.one()
    except NoResultFound:
        with get_db_lock():
            out = Port(name=name)
            try:
                session.add(out)
                session.commit()
            except IntegrityError:
                session.rollback()
                pass
        return get_port(name)

def get_game_mode(name, has_teams):
    q = session.query(GameMode).filter_by(name=name, has_teams=has_teams)
    try:
        return q.one()
    except NoResultFound:
        with get_db_lock():
            out = GameMode(name=name, has_teams=has_teams)
            try:
                session.add(out)
                session.commit()
            except IntegrityError:
                session.rollback()
                pass
        return get_game_mode(name, has_teams)

def get_map(number, name):
    q = session.query(Map).filter_by(number=number, name=name)
    out = q.first()
    if out:
        return out
    with get_db_lock():
        out = Map(number=number, name=name)
        try:
            session.add(out)
            session.commit()
        except IntegrityError:
            session.rollback()
            pass
    return get_map(number, name)

