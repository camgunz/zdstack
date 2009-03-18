import os
import re
import sys
import time
import urllib
import socket
import logging
import logging.handlers

from datetime import datetime, timedelta
from threading import Thread
from cStringIO import StringIO

from pyfileutils import read_file, append_file

from ZDStack.Utils import resolve_file
from ZDStack.ZDSConfigParser import ZDSConfigParser as CP

__all__ = ['SUPPORTED_ENGINE_TYPES', 'HOSTNAME', 'LOOPBACK', 'CONFIGFILE',
           'CONFIGPARSER', 'ZSERV_EXE', 'DATABASE', 'LOGFILE', 'DEBUGGING'
           'PLUGINS', 'DATEFMT', 'DB_ENGINE', 'DB_METADATA', 'DB_SESSION',
           'PlayerNotFoundError', 'DebugTRFH', 'get_hostname', 'get_loopback',
           'get_engine', 'get_metadata', 'get_session', 'get_configfile',
           'set_configfile', 'load_configparser', 'get_configparser',
           'get_plugins', 'get_logfile', 'set_debugging', 'log']

SUPPORTED_ENGINE_TYPES = ('sqlite', 'postgres', 'mysql', 'oracle', 'mssql',
                          'firebird')
HOSTNAME = None
LOOPBACK = None
CONFIGFILE = None
CONFIGPARSER = None
ZSERV_EXE = None
DATABASE = None
LOGFILE = None
DEBUGGING = None
PLUGINS = None
DATEFMT = '%Y-%m-%d %H:%M:%S'
DB_ENGINE = None
DB_METADATA = None
DB_SESSION = None

###
# I'm deciding to only have 1 DB engine, and to make all zservs use it.  I
# suppose I could allow each zserv to have its own engine but that seems a
# little ridiculous.
###

class PlayerNotFoundError(Exception):

    def __init__(self, name=None, ip_address_and_port=None):
        if not name and not ip_address_and_port:
            es = "PlayerNotFoundError requires either a name or an"
            es += "('ip_address', port)"
            raise ValueError(es)
        self.name = name
        self.ip_address_and_port = ip_address_and_port
        if self.ip_address_and_port:
            self.ip_address, self.port = self.ip_address_and_port
        else:
            self.ip_address, self.port = (None, None)
        if name:
            Exception.__init__(self, "Player [%s] not found" % (name))
        else:
            es = "Player Address [%s:%s] not found"
            Exception.__init__(self, es % ip_address_and_port)

class DebugTRFH(logging.handlers.TimedRotatingFileHandler):
    def emit(self, record):
        logging.handlers.TimedRotatingFileHandler.emit(self, record)
        print >> sys.stderr, record.getMessage().strip()

def get_hostname():
    global HOSTNAME
    if not HOSTNAME:
        try:
            __host, __aliases = socket.gethostbyaddr(socket.gethostname())[:-1]
        except socket.gaierror, e:
            es = """\
Could not obtain this machine's fully qualified hostname.  On *NIX machines,
please add a line similar to the following to /etc/hosts:

216.34.181.45 darkstar

Where '216.34.181.45' is replaced by the IP address of the interface ZDStack
should listen on, and 'darkstar' is replaced by the hostname of your machine
(usually found in /etc/HOSTNAME, /etc/hostname, or running the 'hostname'
command).

Error code/message was: %s, %s"""
            raise Exception(es % e.args)
        __hostnames = [x for x in [__host] + __aliases if '.' in x]
        if not __hostnames:
            es = """\
Could not obtain this machine's fully qualified hostname.  On *NIX machines,
please add a line similar to the following to /etc/hosts:

216.34.181.45 darkstar

Where '216.34.181.45' is replaced by the IP address of the interface ZDStack
should listen on, and 'darkstar' is replaced by the hostname of your machine
(usually found in /etc/HOSTNAME, /etc/hostname, or running the 'hostname'
command).

"""
            raise Exception(es)
        HOSTNAME = __hostnames[0]
    return HOSTNAME

def get_loopback():
    global LOOPBACK
    if not LOOPBACK:
        try:
            LOOPBACK = socket.gethostbyname(socket.gethostname())
        except socket.gaierror, e:
            es = """\
Could not obtain this machine's loopback address.  On *NIX machines, please add
a line similar to the following to /etc/hosts:

127.0.0.1 darkstar

Where '127.0.0.1' is replaced by the IP address of the loopback interface, and
'darkstar' is replaced by the hostname of your machine (usually found in
/etc/HOSTNAME, /etc/hostname, or running the 'hostname' command)

Error code/message was: %s, %s"""
            raise Exception(es % e.args)
    return LOOPBACK

def get_engine():
    ###
    # At this point, we are assuming that stats have been enabled.
    ###
    global __ENGINE
    if not __ENGINE:
        db_driver = get_configparser().defaults()['database_engine'].lower()
        if db_driver not in SUPPORTED_ENGINE_TYPES:
            raise ValueError("DB engine %s is not supported" % (db_driver))
        if db_driver == 'sqlite':
            if 'database_name' not in get_configparser().defaults():
                db_name = ':memory:'
            else:
                db_name = get_configparser().defaults()['database_name']
            if not db_name:
                db_name = ':memory:'
            if db_name == ':memory:':
                db_str = 'sqlite://:memory:'
            else:
                db_name = os.path.abspath(db_name) # just to be sure
                if not os.path.isfile(db_name):
                    raise ValueError("SQLite DB file %s not found" % (db_name))
                db_str = 'sqlite:///%s' % (db_name)
        else:
            db_host = get_configparser().defaults()['database_host']
            if port in get_configparser().defaults():
                db_port = get_configparser().defaults()['port']
                if db_port:
                    try:
                        db_port = int(db_port)
                    except:
                        es = "Invalid port number format %s"
                        raise ValueError(es % (db_port))
                db_temp = '%%s://%%s:%%s@%%s:%d/%%s' % (db_port)
                if db_driver == 'mysql' and db_host == 'localhost':
                    db_host = get_loopback()
            else:
                db_port = None
                db_temp = '%s://%s:%s@%s/%s'
            if db_driver == 'mysql':
                ###
                # MySQL's handing of Unicode is apparently a little dumb,
                # so we use SQLAlchemy's.
                ###
                db_temp += '?charset=utf8&use_unicode=0'
            db_user = get_configparser().defaults()['database_user']
            db_pass = get_configparser().defaults()['database_password']
            db_str = db_temp % (db_driver, db_user, db_pass, db_host, db_name)
        from sqlalchemy import create_engine
        if db_driver == 'mysql':
            ###
            # We need to recycle connections every hour or so to avoid MySQL's
            # idle connection timeouts.
            ###
            __ENGINE = create_engine(db_str, pool_recycle=3600)
        else:
            __ENGINE = create_engine(db_str)
    return __ENGINE

def get_metadata():
    global DB_METADATA
    if not DB_METADATA:
        from sqlalchemy import MetaData
        DB_METADATA = MetaData()
        DB_METADATA.bind = get_engine()
    return DB_METADATA

def get_session():
    global DB_SESSION
    if not DB_SESSION:
        from sqlalchemy.orm import sessionmaker
        DB_SESSION = sessionmaker(bind=get_engine())
    return DB_SESSION

def get_configfile():
    global CONFIGFILE
    if not CONFIGFILE:
        possible_config_files = ['./zdstackrc', './zdstack.ini',
                                 '~/.zdstackrc', '~/.zdstack.ini',
                                 '~/.zdstack/zdstackrc',
                                 '~/.zdstack/zdstack.ini',
                                 '/etc/zdstackrc', '/etc/zdstack.ini',
                                 '/etc/zdstack/zdstackrc'
                                 '/etc/zdstack/zdstack.ini']
        possible_config_files = \
                        [resolve_file(x) for x in possible_config_files]
        possible_config_files = \
                        [x for x in possible_config_files if os.path.isfile(x)]
        if not possible_config_files:
            raise ValueError("Could not find a valid configuration file")
        CONFIGFILE = possible_config_files[0]
    return CONFIGFILE

get_configfile()

def set_configfile(config_file):
    global CONFIGFILE
    config_file = resolve_file(config_file)
    if not os.path.isfile(config_file):
        es = "Configuration file [%s] not found"
        raise ValueError(es % (config_file))
    CONFIGFILE = config_file

def load_configparser():
    cp = CP(CONFIGFILE, allow_duplicate_sections=False)
    for section in cp.sections():
        cp.set(section, 'name', section)
    return cp

def get_configparser(reload=False):
    global CONFIGPARSER
    if CONFIGPARSER is None or reload:
        CONFIGPARSER = load_configparser()
    return CONFIGPARSER

def get_zserv_exe():
    global CONFIGPARSER
    global ZSERV_EXE
    if ZSERV_EXE is None:
        if CONFIGPARSER is None:
            get_configparser(config_file)
        if 'zserv_exe' not in CONFIGPARSER.defaults():
            raise ValueError("Option 'zserv_exe' not found")
        else:
            zserv_exe = resolve_file(CONFIGPARSER.defaults()['zserv_exe'])
            if not os.path.isfile(zserv_exe):
                raise ValueError("Could not find zserv executable")
            if not os.access(zserv_exe, os.R_OK | os.X_OK):
                raise ValueError("Could not execute zserv")
        ZSERV_EXE = zserv_exe
    return ZSERV_EXE

def get_plugins(plugins='all', config_file=None):
    global CONFIGPARSER
    global PLUGINS
    if PLUGINS is None:
        if CONFIGPARSER is None:
            get_configparser(config_file)
        d = CONFIGPARSER.defaults()
        if not 'plugin_dir' in d:
            PLUGINS = []
        plugin_dir = d['plugin_dir']
        if not os.path.isdir(resolve_file(plugin_dir)):
            raise ValueError("Plugin folder [%s] not found" % (plugin_dir))
        from ZDStack.Plugins import get_plugins
        PLUGINS = get_plugins(plugin_dir)
    return [x for x in PLUGINS if plugins == 'all' or x.__name__ in plugins]

def get_logfile(log_file=None, config_file=None):
    global CONFIGPARSER
    global LOGFILE
    if LOGFILE is None:
        if log_file:
            LOGFILE = log_file
        else:
            if CONFIGPARSER is None:
                get_configparser(config_file)
            rootfolder = get_configparser().defaults()['rootfolder']
            LOGFILE = os.path.join(rootfolder, 'ZDStack.log')
    return LOGFILE

def set_debugging(debugging, log_file=None, config_file=None):
    global LOGFILE
    global DEBUGGING
    if LOGFILE is None:
        get_logfile(log_file, config_file)
    if debugging:
        __log_level = logging.DEBUG
        __log_format = '[%(asctime)s] '
        __log_format += '%(filename)-14s - %(module)-14s - %(funcName)-16s '
        __log_format += '- %(lineno)-4d: '
        __log_format += '%(levelname)-8s %(message)s'
        __handler_class = DebugTRFH
        DEBUGGING = True
    else:
        __log_level = logging.INFO
        __log_format = '[%(asctime)s] '
        __log_format += '%(levelname)-8s %(message)s'
        __handler_class = logging.handlers.TimedRotatingFileHandler
        DEBUGGING = False
    formatter = logging.Formatter(__log_format, DATEFMT)
    handler = __handler_class(LOGFILE, when='midnight', backupCount=4)
    handler.setFormatter(formatter)
    logging.RootLogger.root.addHandler(handler)
    logging.RootLogger.root.setLevel(__log_level)
    handler.setLevel(__log_level)

set_debugging(False)

