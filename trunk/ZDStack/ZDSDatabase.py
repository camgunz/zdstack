from __future__ import with_statement

import logging
import datetime

from contextlib import contextmanager

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exceptions import IntegrityError

from ZDStack import get_db_lock, db_is_noop, get_session_class
from ZDStack.ZDSModels import *

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
            # logging.debug("Beginning a transaction")
            with s.begin():
                ###
                # Implicitly commits at the end of the block.
                ###
                # logging.debug("Inside transaction")
                yield s
            # logging.debug("Transaction completed")
        except Exception, e:
            # logging.debug("Error inside transaction: %s" % (e))
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
    return _locked_session(get_global=False, remove=True)

def global_session():
    return _locked_session(get_global=True, remove=False)

def persist(model, update=False, session=None):
    """Persists a model.

    model:   an instance of an Entity subclass.
    update:  an optional boolean that, if given, indicates that the
             model already exists in the database and just needs to be
             updated.  False by default, meaning the model will be
             INSERTed.
    session: optional, if given uses the session instead of acquiring
             the global DB lock and creating its own.

    This is a no-op if DB_NOOP is set, and DB_NOOP is set when
    using a full RDBMS.

    """
    if db_is_noop():
        return model
    if update:
        def blah(s):
            # logging.debug("Merging: [%s]" % (model))
            s.merge(model)
            return model
    else:
        def blah(s):
            # logging.debug("Adding: [%s]" % (model))
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

def _wrap_func(func):
    logging.debug("Wrapping %s" % (func.__name__))
    def wrapped_func(*args, **kwargs):
        # logging.debug("Running %s, %s, %s" % (func.__name__, str(args),
        #                                       str(kwargs)))
        if not kwargs.get('session', None):
            with global_session() as session:
                # logging.debug("Using session [%s]" % (session))
                kwargs['session'] = session
                return func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    return wrapped_func

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

def _get_weapon(name, is_suicide, session):
    q = session.query(Weapon).filter_by(name=name, is_suicide=is_suicide)
    try:
        return q.one()
    except NoResultFound:
        return persist(Weapon(name=name, is_suicide=is_suicide),
                       session=session)

def _get_alias(name, ip_address, session, round=None):
    q = session.query(Alias).filter_by(name=name, ip_address=ip_address)
    out = q.first()
    if out:
        return out
    return persist(Alias(name=name, ip_address=ip_address), session=session)

def _get_team_color(color, session):
    q = session.query(TeamColor).filter_by(color=color)
    try:
        return q.one()
    except NoResultFound:
        return persist(TeamColor(color=color), session=session)

def _get_port(name, session):
    q = session.query(Port).filter_by(name=name)
    try:
        return q.one()
    except NoResultFound:
        return persist(Port(name=name), session=session)

def _get_game_mode(name, has_teams, session):
    q = session.query(GameMode).filter_by(name=name, has_teams=has_teams)
    try:
        return q.one()
    except NoResultFound:
        return persist(GameMode(name=name, has_teams=has_teams),
                       session=session)

def _get_map(number, name, session):
    q = session.query(Map).filter_by(number=number, name=name)
    out = q.first()
    if out:
        return out
    return persist(Map(number=number, name=name), session=session)

def _get_round(game_mode, map, session, start_time=None):
    start_time = start_time or datetime.datetime.now()
    r = persist(Round(game_mode=game_mode, map=map, start_time=start_time),
                session=session)
    return r

get_weapon = _wrap_func(_get_weapon)
get_alias = _wrap_func(_get_alias)
get_team_color = _wrap_func(_get_team_color)
get_port = _wrap_func(_get_port)
get_game_mode = _wrap_func(_get_game_mode)
get_map = _wrap_func(_get_map)
get_round = _wrap_func(_get_round)

