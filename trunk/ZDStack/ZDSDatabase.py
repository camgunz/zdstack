from __future__ import with_statement

import datetime

from contextlib import contextmanager

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exceptions import IntegrityError, OperationalError

from ZDStack import get_db_lock, get_session_class, get_zdslog
from ZDStack.Utils import requires_lock
from ZDStack.ZDSModels import *

zdslog = get_zdslog()

__GLOBAL_SESSION = None

@contextmanager
@requires_lock(get_db_lock())
def _locked_session(get_global=False, remove=False):
    zdslog.debug('Acquired DB lock')
    global __GLOBAL_SESSION
    SessionClass = get_session_class()
    with get_db_lock():
        if get_global:
            __GLOBAL_SESSION = __GLOBAL_SESSION or SessionClass()
            s = __GLOBAL_SESSION
        else:
            s = SessionClass()
        try:
            try:
                s.begin()
                yield s
                s.commit()
            except OperationalError, e:
                zdslog.error("Got an operational error: %s" % (e))
                ###
                # Try again - MySQL could've just timed out.
                ###
                s.commit()
        except Exception, e:
            zdslog.error("Error inside transaction: %s" % (e))
            import traceback
            zdslog.debug("Traceback: %s" % (traceback.format_exc()))
            s.rollback()
            zdslog.info("Successfully rolled back")
            raise
        finally:
            if remove:
                ###
                # I never want to see this session again!
                ###
                SessionClass.remove()
        

def new_session():
    """Creates a new Session instance.
    
    :returns: a new Session instance
    :rtype: Session

    This is a contextmanager that opens a transaction, committing or
    rolling back as necessary.

    """
    return _locked_session(get_global=False, remove=True)

def global_session():
    """Gets the global Session instance.
    
    :returns: the global Session instance
    :rtype: Session

    This is a contextmanager that opens a transaction, committing or
    rolling back as necessary.

    """
    return _locked_session(get_global=True, remove=False)

def persist(model, update=False, session=None):
    """Persists a model.

    :param model: the model to persist.
    :type model: object
    :param update: whether or not to UPDATE the model, or INSERT it as
                   completely new; False by default
    :type update: boolean
    :param session: the session to use, if none is given, the global
                    session is used
    :type session: Session
    :returns: the given model

    """
    zdslog.debug('Persisting [%s]' % (model))
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
        zdslog.debug('Using existing session %s' % (session))
        return blah(session)
    else:
        ###
        # There is no current session, so we need to create one.  The commit
        # will still happen outside of this function/block however.
        ###
        zdslog.debug('Trying to use global session')
        with global_session() as session:
            zdslog.debug('Using global session %s' % (session))
            return blah(session)

def requires_session(func):
    """A function decorator executing the function inside a session.

    If no session is given with the keyword argument 'session', the
    global session is used.

    """
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
# TODO:
#
#   Because Sessions freak out when their database connection dies, we simply
#   can't hold onto models anymore.  Fortunately, the only things we hold onto
#   at this point are Rounds and Aliases (ZServ and ZDSPlayer respectively),
#   so these attributes need to be replaced with methods, and those methods
#   need to call functions here... which don't exist yet.
###

