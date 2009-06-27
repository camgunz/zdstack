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

