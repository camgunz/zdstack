from __future__ import with_statement

import datetime

from contextlib import contextmanager

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exceptions import IntegrityError

from ZDStack import get_db_lock, get_session_class, get_zdslog
from ZDStack.Utils import requires_lock
from ZDStack.ZDSModels import *

zdslog = get_zdslog()

__GLOBAL_SESSION = None

###
# SQLite strategy:
#
# Problem: SQLite connections can't be shared across threads.
# Problem: SQLite can't handle two transactions committing at the same time.
#
# Solutions:
#
#   - Disable SQLAlchemy autoflushing, enable autocommitting (so there is no
#     persistent transaction)
#   - Set 'check_same_thread' to False when creating the engine
#   - Set 'isolation_level' to 'IMMEDIATE' when creating the engine
#   - Use a global (contextual) session by default
#   - Employ a lock to ensure only 1 thread is accessing the session at a time
#   - Return all models as bound to the global (contextual) session
#
# Real database strategy:
#
# Problem: Using the same strategy as for SQLite can seriously hurt performance
#          when using a RDBMS that can handle concurrent access.
#
# Solutions (in contrast to SQLite solutions):
#
#   - Enable SQLAlchemy autoflushing, disable autocommitting (so there is
#     always a persistent transaction)
#   - Replace the session lock with a dummy lock, which never actually locks
#     at all
#   - Because autoflushing takes care of updates and refreshes, set the
#     functions ZDStack uses to explicitly do those things to be no-ops
###

@contextmanager
@requires_lock(get_db_lock())
def _locked_session(get_global=False, remove=False):
    global __GLOBAL_SESSION
    SessionClass = get_session_class()
    with get_db_lock():
        if get_global:
            __GLOBAL_SESSION = __GLOBAL_SESSION or SessionClass()
            s = __GLOBAL_SESSION
        else:
            s = SessionClass()
        try:
            # zdslog.debug("Beginning a transaction")
            with s.begin():
                ###
                # Implicitly commits at the end of the block.
                ###
                # zdslog.debug("Inside transaction")
                yield s
            # zdslog.debug("Transaction completed")
        except Exception, e:
            # zdslog.debug("Error inside transaction: %s" % (e))
            s.rollback()
            raise
        finally:
            ###
            # I think closing the session causes problems with Models not
            # being bound to it, so we'll skip closing it for now.
            #
            # s.close()
            #
            ###
            if remove:
                ###
                # I never want to see this session again!
                ###
                SessionClass.remove()
        

def new_session():
    """Returns a new Session instance."""
    return _locked_session(get_global=False, remove=True)

def global_session():
    """Returns the global Session instance."""
    return _locked_session(get_global=True, remove=False)

def persist(model, update=False, session=None):
    """Persists a model.

    :param model: the model to persist.
    :type model: sqlalchemy.ext.declarative.Base
    :param update: whether or not to UPDATE the model, or INSERT it as
                   completely new; False by default
    :type update: boolean
    :param session: the session to use, if none is given, the global
                    session is used
    :type session: Session

    """
    if update:
        def blah(s):
            zdslog.debug("Merging: [%s]" % (model))
            s.merge(model)
            return model
    else:
        def blah(s):
            zdslog.debug("Adding: [%s]" % (model))
            s.add(model)
            return model
    if session:
        ###
        # We are within a new_session() block, so all of our locking and
        # committing is already handled for us.
        ###
        return blah(session)
    else:
        ###
        # There is no current session, so we need to create one.  The commit
        # will still happen outside of this function/block however.
        ###
        with global_session() as session:
            return blah(session)

def requires_session(func):
    zdslog.debug("Wrapping %s" % (func.__name__))
    def wrapper(*args, **kwargs):
        # zdslog.debug("Running %s, %s, %s" % (func.__name__, str(args),
        #                                       str(kwargs)))
        if kwargs.get('session', None):
            return func(*args, **kwargs)
        else:
            with global_session() as session:
                # zdslog.debug("Using session [%s]" % (session))
                kwargs['session'] = session
                return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__dict__ = func.__dict__
    wrapper.__doc__ = func.__doc__
    return wrapper

###
# What follows is ridiculous, and I can't imagine this is what you are
# actually supposed to do.  But FUCK if I can't figure out how to get
# SQLAlchemy to think for itself and not INSERT rows that already exist.
# Goddamn.
#
# It's very simple:
#
#   I'd rather not manually do a query to see if the object I'm about to create
#     has ever, in the entire goddamn history of the database, been
#     instantiated before.
#   I don't want to subclass things or create stupid MixIns or find random
#     configuration "DSL" methods with obscure, random names to do this.
#   Holy shit, I use threads.  I don't want everything to be fucking destroyed
#     as a result.
#
# OK, rant over.  Shit.
###

###
# TODO:
#
#   Because Sessions freak out when their database connection dies, we simply
#   can't hold onto models anymore.  Fortunately, the only things we hold onto
#   at this point are Rounds and Aliases (ZServ and ZDSPlayer respectively),
#   so these attributes need to be replaced with methods, and those methods
#   need to call functions here... which don't exist yet.
###

@requires_session
def get_weapon(name, is_suicide, session):
    """Gets a Weapon.
    
    :param name: the name of the Weapon to get
    :type name: string
    :param is_suicide: whether or not the Weapon is a suicide
    :type is_suicide: boolean
    :param session: the session to use, if none is given, the global
                    session is used
    :type session: Session

    """
    q = session.query(Weapon).filter_by(name=name, is_suicide=is_suicide)
    try:
        return q.one()
    except NoResultFound:
        return persist(Weapon(name=name, is_suicide=is_suicide),
                       session=session)

@requires_session
def get_alias(name, ip_address, session, round=None):
    """Gets an Alias.
    
    :param name: the name of the Alias to get
    :type name: string
    :param session: the session to use, if none is given, the global
                    session is used
    :type session: Session
    :param round: optional, the round to which this alias belongs
    :type round: Round

    """
    q = session.query(Alias).filter_by(name=name, ip_address=ip_address)
    out = q.first()
    if out:
        return out
    alias = Alias(name=name, ip_address=ip_address)
    if round and not round in alias.rounds:
        alias.rounds.append(round)
    return persist(alias, session=session)

@requires_session
def get_team_color(color, session):
    """Gets a TeamColor.
    
    :param color: the color of the TeamColor to get
    :type color: string
    :param session: the session to use, if none is given, the global
                    session is used
    :type session: Session

    """
    q = session.query(TeamColor).filter_by(color=color)
    try:
        return q.one()
    except NoResultFound:
        return persist(TeamColor(color=color), session=session)

@requires_session
def get_port(name, session):
    """Gets a Port.
    
    :param name: the name of the Port to get
    :type name: string
    :param session: the session to use, if none is given, the global
                    session is used
    :type session: Session

    """
    q = session.query(Port).filter_by(name=name)
    try:
        return q.one()
    except NoResultFound:
        return persist(Port(name=name), session=session)

@requires_session
def get_game_mode(name, has_teams, session):
    """Gets a GameMode.
    
    :param name: the name of the GameMode to get
    :type name: string
    :param session: the session to use, if none is given, the global
                    session is used
    :type session: Session

    """
    q = session.query(GameMode).filter_by(name=name, has_teams=has_teams)
    try:
        return q.one()
    except NoResultFound:
        return persist(GameMode(name=name, has_teams=has_teams),
                       session=session)

@requires_session
def get_map(number, name, session):
    """Gets a Map.
    
    :param number: the number of the Map to get
    :type number: int
    :param name: the name of the Map to get
    :type name: string
    :param session: the session to use, if none is given, the global
                    session is used
    :type session: Session

    """
    q = session.query(Map).filter_by(number=number, name=name)
    out = q.first()
    if out:
        return out
    return persist(Map(number=number, name=name), session=session)

@requires_session
def get_round(game_mode, map, session, start_time=None):
    """Gets a Round.
    
    :param game_mode: the GameMode of the Round to get
    :type game_mode: GameMode
    :param map: the Map of the Round to get
    :type map: Map
    :param session: the session to use, if none is given, the global
                    session is used
    :type session: Session

    """
    start_time = start_time or datetime.datetime.now()
    r = persist(Round(game_mode=game_mode, map=map, start_time=start_time),
                session=session)
    return r

