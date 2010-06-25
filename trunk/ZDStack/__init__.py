import os
import sys
import stat
import time
import socket
import urllib
import logging
from logging.handlers import TimedRotatingFileHandler
import datetime

from threading import Lock
from decimal import Decimal
from contextlib import contextmanager

from ZDStack.Utils import resolve_path, create_file
from ZDStack.ZDSConfigParser import ZDSConfigParser as CP
from ZDStack.ZDSConfigParser import RawZDSConfigParser as RCP

###
# ORM Stuff
###

from sqlalchemy import create_engine, MetaData, select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session, sessionmaker, relation, mapper, \
                           column_property
from sqlalchemy.pool import StaticPool, NullPool
from sqlalchemy.orm.exc import NoResultFound

DB_SESSION_CLASS = None
DB_METADATA = None
DB_AUTOFLUSH = None
DB_AUTOCOMMIT = None

###
# End ORM Stuff
###

__all__ = [
  'SUPPORTED_ENGINE_TYPES',
  'NO_AUTH_REQUIRED',
  'HOSTNAME',
  'LOOPBACK',
  'DEVNULL',
  'CONFIGFILE',
  'CONFIGPARSER',
  'DEBUGGING',
  'PLUGINS',
  'DATEFMT',
  'JSON_MODULE',
  'RPC_CLASS',
  'RPC_PROXY_CLASS',
  'TEAM_COLORS',
  'TICK',
  'MAX_TIMEOUT',
  'DIE_THREADS_DIE',
  'ZDSLOG',
  'JSONNotFoundError',
  'PlayerNotFoundError',
  'TeamNotFoundError',
  'ZServNotFoundError',
  'RPCAuthenticationError',
  'DebugTRFH',
  'DB_SESSION_CLASS',
  'DB_METADATA',
  'DB_ENGINE',
  'DB_AUTOFLUSH',
  'DB_AUTOCOMMIT',
  'ZDAEMON_BANLIST_URL',
  'get_hostname',
  'get_loopback',
  'get_engine',
  'get_metadata',
  'get_db_lock',
  'get_session_class',
  'get_configfile',
  'set_configfile',
  'load_configparser',
  'get_configparser',
  'get_zdaemon_banlist_data',
  'get_zdaemon_banlist_file',
  'get_server_proxy',
  'get_plugins',
  'set_debugging',
  'get_zdslog',
  'get_debugging'
]

REQUIRED_GLOBAL_CONFIG_OPTIONS = (
    'zdstack_username',
    'zdstack_password',
    'zdstack_port',
    'zdstack_rpc_protocol',
    'zdstack_log_folder',
    'zdstack_pid_file',
    'zdstack_zserv_folder',
    'zdstack_plugin_folder',
    'zdstack_iwad_folder',
    'zdstack_wad_folder',
    'zdstack_master_banlist_file',
    'zdstack_banlist_file',
    'zdstack_whitelist_file'
)

REQUIRED_SERVER_CONFIG_OPTIONS = (
    'zserv_exe',
    'iwad',
    'enable_events',
    'enable_stats',
    'enable_plugins',
    'hostname',
    'admin_email',
    'website',
    'motd',
    'advertise',
    'skill',
    'mode',
    'port'
)

REQUIRED_GLOBAL_VALID_FOLDERS = (
    ('zdstack_log_folder',    os.R_OK | os.W_OK | os.X_OK),
    ('zdstack_zserv_folder',  os.R_OK | os.W_OK | os.X_OK),
    ('zdstack_plugin_folder', os.R_OK | os.X_OK),
    ('zdstack_iwad_folder',   os.R_OK | os.X_OK),
    ('zdstack_wad_folder',    os.R_OK | os.X_OK)
)

REQUIRED_GLOBAL_VALID_FILES = (
    ('zdstack_banlist_file',        os.R_OK | os.W_OK),
    ('zdstack_whitelist_file',      os.R_OK | os.W_OK),
    ('zdstack_master_banlist_file', os.R_OK | os.W_OK)
)

REQUIRED_SERVER_VALID_FILES = (
  ('zserv_exe', os.R_OK | os.X_OK, False),
  ('iwad',      os.R_OK,           False)
)

SUPPORTED_ENGINE_TYPES = (
    'sqlite',
    'postgresql',
    'mysql',
    'oracle',
    'mssql',
    'firebird'
)

class DummyLog(object):

    def debug(self, s):
        pass

    def info(self, s):
        pass

    def error(self, s):
        raise Exception(s)

SUPPORTED_GAME_MODES = ('ctf', 'coop', 'duel', 'ffa', 'teamdm')

NO_AUTH_REQUIRED = ('list_zserv_names', 'get_zserv_info', 'get_all_zserv_info')

DEVNULL = open(os.devnull, 'w')
DATEFMT = '%Y-%m-%d %H:%M:%S.%f'
TEAM_COLORS = ('red', 'blue', 'green', 'white')
TICK = Decimal('0.027')
MAX_TIMEOUT = 1
DIE_THREADS_DIE = False
ZDAEMON_BANLIST_URL = 'http://zdaemon.ath.cx/bans/'
URL_OPENER = urllib.FancyURLopener()

###
# These are all internal __init__ globals, and they all have getters that
# should be used instead of importing them.  Setting the value of these
# variables does work, however; the getters only modify these if they are
# None.
###
HOSTNAME = None
LOOPBACK = None
CONFIGFILE = None
CONFIGPARSER = None
DEBUGGING = None
PLUGINS = None
ZDAEMON_BANLIST_FILE = None
DB_LOCK = None
###
# I'm deciding to only have 1 DB engine, and to make all zservs use it.  I
# suppose I could allow each zserv to have its own engine but that seems a
# little ridiculous.
###
DB_ENGINE = None
JSON_MODULE = None
RPC_CLASS = None
RPC_PROXY_CLASS = None
ZDSLOG = DummyLog()

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

class TeamNotFoundError(Exception):

    def __init__(self, color):
        Exception.__init__(self, "%s Team not found" % (color.capitalize()))

class ZServNotFoundError(Exception):

    def __init__(self, zserv_name):
        Exception.__init__(self, "ZServ [%s] not found" % (zserv_name))

class RPCAuthenticationError(Exception):

    def __init__(self, username):
        Exception.__init__(self, "Authentication failed for [%s]" % (username))

class DebugFormatter(logging.Formatter):

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if not datefmt:
            t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
            s = "%s,%03d" % (t, record.msecs)
        else:
            microseconds = Decimal(str(record.msecs)) * 1000
            t = [ct[0], ct[1], ct[2], ct[3], ct[4], ct[5], microseconds]
            dt = datetime.datetime(*t)
            s = dt.strftime(datefmt)
            ###
            # Python 2.5 doesn't interpolate microseconds for '%f', so we do it
            # here manually if necessary.
            ###
            microseconds = str(dt.microsecond).zfill(6)
            while '%f' in s:
                s = s.replace('%f', microseconds)
        return s

class JSONNotFoundError(Exception):

    def __init__(self):
        es = "Using JSON-RPC requires either Python 2.6 (or higher) or "
        es += "simplejson"
        Exception.__init__(self, es)

def get_hostname():
    """Gets this machine's public-facing hostname.

    :rtype: string
    :returns: the machine's public-facing hostname.

    """
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
    """Gets this machine's private loopback address.

    :rtype: string
    :returns: the machine's private loopback address

    """
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

def get_configfile():
    """Gets the location of the ZDStack configuration file.

    :rtype: string
    :returns: the full resolved path to the ZDStack configuration file

    """
    global CONFIGFILE
    if not CONFIGFILE:
        if os.name == 'nt':
            possible_config_files = [
                'zdstackrc',
                'zdstack.ini',
                '~\\ZDStack\\zdstackrc',
                '~\\ZDStack\\zdstack.ini',
            ]
        else:
            possible_config_files = [
                './zdstackrc',
                './zdstack.ini',
                '~/.zdstackrc',
                '~/.zdstack.ini',
                '~/.zdstack/zdstackrc',
                '~/.zdstack/zdstack.ini',
                '/etc/zdstackrc',
                '/etc/zdstack.ini',
                '/etc/zdstack/zdstackrc'
                '/etc/zdstack/zdstack.ini'
            ]
        possible_config_files = \
                        [resolve_path(x) for x in possible_config_files]
        possible_config_files = \
                        [x for x in possible_config_files if os.path.isfile(x)]
        if not possible_config_files:
            raise Exception("Could not find a valid configuration file")
        CONFIGFILE = possible_config_files[0]
    return CONFIGFILE

def set_configfile(config_file):
    """Sets the location of the ZDStack configuration file.

    :param config_file: the new configuration file
    :type config_file: string

    'config_file' will be run through 'resolve_file()'

    """
    global CONFIGFILE
    config_file = resolve_path(config_file)
    if not os.path.isfile(config_file):
        es = "Configuration file [%s] not found"
        raise ValueError(es % (config_file))
    CONFIGFILE = config_file

def check_server_config_section(server_name, config):
    """Checks an individual server's configuration section.

    :param server_name: the name of the server whose configuration
                        section is to be checked
    :type server_name"
    :param config: configuration options and values
    :type config: :class:`~ZDStack.ZDSConfigParser`

    """
    ports = [config.get(s, 'port') for s in config.sections()]
    d = dict(config.items(server_name))
    for x in REQUIRED_SERVER_CONFIG_OPTIONS:
        if x not in d or not d[x]:
            es = "Required server option %s not found for server [%s]"
            raise ValueError(es % (x, s))
    for fo, m, can_create in REQUIRED_SERVER_VALID_FILES:
        f = config.getpath(s, fo)
        if not (os.path.isfile(f) or os.path.islink(f)):
            if can_create:
                try:
                    create_file(f)
                except Exception, e:
                    raise ValueError("Could not create %s: %s" % (f, e))
            else:
                raise ValueError("Couldn't locate %s" % (fo))
        if not os.access(f, m):
            raise ValueError("Insufficient access provided for %s" % (f))
    if d['mode'].lower() not in SUPPORTED_GAME_MODES:
        raise ValueError("Unsupported game mode %s" % (d['mode']))
    if ports.count(d['port']) > 1:
        es = "%s's port (%s) is already in use"
        raise ValueError(es % (d['name'], d['port']))
    if 'fakezserv' in d['zserv_exe']:
        if not 'fake_logfile' in d:
            es = "When using 'fakezserv', the option 'fake_logfile' must "
            es += "be defined"
            raise ValueError(es)
        f = config.getpath(s, 'fake_logfile')
        if not os.path.isfile(f):
            es = "Could not locate fake logfile [%s]"
            raise ValueError(es % (d['fake_logfile']))

def load_configparser(check=False):
    """Loads the ZDStack configuration file into a ConfigParser.
    
    :param check: whether or not to check some files and folders for
                  existence, proper permissions, etc, defaults to False
    :type check: boolean
    :rtype: :class:`~ZDStack.ZDSConfigParser.ZDSConfigParser`
    
    """
    global RPC_CLASS
    global RPC_PROXY_CLASS
    global DEBUGGING
    cp = CP(get_configfile())
    for section in cp.sections():
        cp.set(section, 'name', section)
    for x in REQUIRED_GLOBAL_CONFIG_OPTIONS:
        if not cp.get('DEFAULT', x, default=False):
            raise ValueError("Required global option %s not found" % (x))
    for fo, m in REQUIRED_GLOBAL_VALID_FOLDERS:
        f = cp.getpath('DEFAULT', fo)
        if not os.path.isdir(f):
            try:
                os.mkdir(f)
            except Exception, e:
                raise Exception("Could not make folder %s: %s" % (fo, e))
        if not os.access(f, m):
            raise ValueError("Insufficient access provided for %s" % (fo))
    for fo, m in REQUIRED_GLOBAL_VALID_FILES:
        f = cp.getpath('DEFAULT', fo, None)
        if not (os.path.isfile(f) or os.path.islink(f)):
            try:
                create_file(f)
            except Exception, e:
                raise ValueError("Could not create %s: %s" % (f, e))
        if not os.access(f, m):
            raise ValueError("Insufficient access provided for %s" % (f))
        # cp.set('DEFAULT', fo, f)
    if check:
        for s in cp.sections():
            check_server_config_section(s, cp)
    ###
    # Below are some checks for specific options & values
    ###
    ###
    # Check RPC protocol is supported
    ###
    zrp = cp.get('DEFAULT', 'zdstack_rpc_protocol', 'xml-rpc').lower()
    rp = zrp.lower()
    if rp in ('jsonrpc', 'json-rpc'):
        cp.set('DEFAULT', 'zdstack_rpc_protocol', 'json-rpc')
        global JSON_MODULE
        ###
        # Python 2.6 and up have a 'json' module we can use.  Otherwise we
        # require simplejson.
        ###
        try:
            import json
            JSON_MODULE = json
        except ImportError:
            try:
                import simplejson
                JSON_MODULE = simplejson
            except ImportError:
                raise JSONNotFoundError
    elif rp in ('xmlrpc', 'xml-rpc'):
        cp.set('DEFAULT', 'zdstack_rpc_protocol', 'xml-rpc')
    else:
        es = "RPC Protocol [%s] not supported"
        raise ValueError(es % (zrp))
    ###
    # Resolve RPC hostname.
    ###
    if cp.get('DEFAULT', 'zdstack_rpc_hostname', 'localhost') == 'localhost':
        cp.set('DEFAULT', 'zdstack_rpc_hostname', get_loopback())
    ###
    # Make sure the folder for the zserv processes exists.
    ###
    zserv_folder = cp.getpath('DEFAULT', 'zdstack_zserv_folder')
    if not os.path.isdir(zserv_folder):
        try:
            os.mkdir(zserv_folder)
        except Exception, e:
            es = "Error: ZServ Server folder %s is not valid: %s"
            raise ValueError(es % (zserv_folder, e))
    ###
    # Make sure the folder for the log files exists.
    ###
    log_folder = cp.getpath('DEFAULT', 'zdstack_log_folder')
    if not os.path.isdir(log_folder):
        try:
            os.mkdir(log_folder)
        except Exception, e:
            es = "Error: ZDStack Log Folder %s is not valid: %s"
            raise ValueError(es % (log_folder, e))
    ###
    # Make sure the folder for the plugins exists.
    ###
    plugin_folder = cp.getpath('DEFAULT', 'zdstack_plugin_folder')
    if not os.path.isdir(plugin_folder):
        try:
            os.mkdir(plugin_folder)
        except Exception, e:
            es = "Error: ZDStack Plugin Folder %s is not valid: %s"
            raise ValueError(es % (plugin_folder, e))
    if DEBUGGING is None:
        set_debugging(False)
    return cp
    ###
    # Check for duplicate ports.
    ###
    seen_ports = set()
    for section in cp.sections():
        port = cp.getint(section, 'port')
        if port in seen_ports:
            es = "Server [%s] has duplicate port [%s]"
            raise ValueError(es % (section, port))
        else:
            seen_ports.add(port)
    return cp

def _get_embedded_engine(db_engine, cp):
    """This returns an engine for an embedded database.

    db_engine: a string representing the database engine to use.
    cp:        a ZDSRawConfigParser or subclass.

    Certain things need to be set appropriately to ensure error-free 
    use of embedded databases, and this method sets them.

    """
    ZDSLOG.debug("Getting embedded engine")
    if db_engine == 'sqlite':
        db_name = cp.get('DEFAULT', 'zdstack_database_name', ':memory:')
    else:
        db_name = cp.get('DEFAULT', 'zdstack_database_name', False)
        if not db_name:
            es = "Required global option zdstack_database_name not found"
            raise ValueError(es)
        elif db_name == ':memory:':
            es = ":memory: is only valid when using the SQLite database engine"
            raise ValueError(es)
    db_str = '%s://' % (db_engine)
    if db_name == ':memory:':
        db_str += '/:memory:'
    else:
        db_name = resolve_path(db_name) # just to be sure
        if not os.path.isfile(db_name):
            es = "Embedded DB file %s not found, will create new DB"
            ZDSLOG.info(es % (db_name))
        db_str += '/' + db_name
    if db_engine == 'sqlite':
        cd = {'check_same_thread': False, 'isolation_level': 'IMMEDIATE'}
        e = create_engine(db_str, poolclass=StaticPool, connect_args=cd)
    else:
        e = create_engine(db_str, poolclass=StaticPool)
    return e

def _get_full_engine(db_engine, cp):
    """This returns an engine for a full RDBMS.

    db_engine: a string representing the database engine to use.
    cp:        a ZDSRawConfigParser or subclass.

    Certain things need to be set appropriately to ensure performant
    use of full databases, and this method sets them.

    """
    ZDSLOG.debug("Getting full engine")
    db_str = '%s://' % (db_engine.replace('-', ''))
    ###
    # Some databases might be configured for user-less/password-less
    # access (potentially dumb, but w/e).
    ###
    db_user = None
    db_pass = None
    ###
    # Be a little flexible in the labeling of the db user & pw fields
    ###
    if cp.get('DEFAULT', 'zdstack_database_user', False):
        db_user = cp.get('DEFAULT', 'zdstack_database_user')
    elif cp.get('DEFAULT', 'zdstack_database_username', False):
        db_user = cp.get('DEFAULT', 'zdstack_database_username')
    if cp.get('DEFAULT', 'zdstack_database_pass', False):
        db_pass = cp.get('DEFAULT', 'zdstack_database_pass')
    elif cp.get('DEFAULT', 'zdstack_database_password', False):
        db_pass = cp.get('DEFAULT', 'zdstack_database_password')
    elif cp.get('DEFAULT', 'zdstack_database_passwd', False):
        db_pass = cp.get('DEFAULT', 'zdstack_database_passwd')
    if db_user:
        db_str += urllib.quote(db_user)
        if db_pass:
            db_str += ':' + urllib.quote(db_pass)
        db_str += '@'
    elif db_pass:
        es = "Cannot give a database password without a database user"
        raise ValueError(es)
    db_host = urllib.quote(cp.get('DEFAULT', 'zdstack_database_host'))
    if db_host == 'localhost' and db_engine != 'mysql':
        ###
        # MySQL supports local socket connections.  Everything else needs
        # a real socket though.
        ###
        db_host = get_loopback()
    db_str += db_host
    db_port = cp.get('DEFAULT', 'zdstack_database_port', False)
    if db_port:
        int(db_port) # will give an error if the port is malformed
        db_str += ':' + db_port
    db_name = cp.get('DEFAULT', 'zdstack_database_name', False)
    if not db_name:
        es = "Required global option zdstack_database_name not found"
        raise ValueError(es)
    db_str += '/' + urllib.quote(db_name)
    if db_engine == 'mysql':
        ###
        # MySQL's handing of Unicode is apparently a little dumb,
        # so we use SQLAlchemy's.
        ###
        db_str += '?charset=utf8&use_unicode=0'
    ZDSLOG.debug("Creating engine from DB str: [%s]" % (db_str))
    if db_engine == 'mysql':
        ###
        # We need to recycle connections every hour or so to avoid MySQL's
        # idle connection timeouts.
        #
        # Also MySQL is a faggot, and will totally just disconnect us.  Jesus.
        ###
        return create_engine(db_str, poolclass=NullPool, pool_recycle=3600)
    else:
        return create_engine(db_str)

def get_engine():
    """Gets the database engine.

    :rtype: an SQLAlchemy Engine instance.

    """
    ###
    # At this point, we are assuming that stats have been enabled.
    ###
    ZDSLOG.debug("Getting engine")
    global DB_ENGINE
    global DB_AUTOFLUSH
    global DB_AUTOCOMMIT
    global DB_LOCK
    DB_LOCK = Lock()
    if not DB_ENGINE:
        cp = get_configparser()
        db_engine = cp.get('DEFAULT', 'zdstack_database_engine', 'sqlite')
        db_engine = db_engine.lower()
        if db_engine not in SUPPORTED_ENGINE_TYPES:
            raise ValueError("DB engine %s is not supported" % (db_engine))
        if db_engine in ('sqlite', 'firebird'):
            ###
            # Firebird isn't necessarily embedded, so we should sort this out
            # somehow.
            ###
            DB_ENGINE = _get_embedded_engine(db_engine, cp)
            DB_AUTOFLUSH, DB_AUTOCOMMIT = (True, True)
        else:
            DB_ENGINE = _get_full_engine(db_engine, cp)
            DB_AUTOFLUSH, DB_AUTOCOMMIT = (True, True)
    return DB_ENGINE

def get_metadata():
    """Gets the database's metadata.

    :rtype: an SQLAlchemy MetaData instance.

    """
    global DB_METADATA
    if not DB_METADATA:
        DB_METADATA = MetaData()
        DB_METADATA.bind = get_engine()
    return DB_METADATA

def get_session_class():
    """Gets the database Session class.

    :rtype: an SQLAlchemy Session class.

    """
    global DB_SESSION_CLASS
    if not DB_SESSION_CLASS:
        if None in (DB_ENGINE, DB_AUTOFLUSH, DB_AUTOCOMMIT):
            raise Exception("Database engine has not been created yet.")
        ZDSLOG.debug("autoflush is %s" % (DB_AUTOFLUSH))
        ZDSLOG.debug("autocommit is %s" % (DB_AUTOCOMMIT))
        DB_SESSION_CLASS = scoped_session(sessionmaker())
        DB_SESSION_CLASS.configure(autoflush=DB_AUTOFLUSH,
                                   autocommit=DB_AUTOCOMMIT)
        DB_SESSION_CLASS.bind = DB_ENGINE
    return DB_SESSION_CLASS

def get_db_lock():
    """Gets the global DB lock.

    :rtype: :class:`~threading.Lock`
    :returns: the global database lock, although doesn't acquire it

    """
    global DB_LOCK
    DB_LOCK = DB_LOCK or Lock()
    return DB_LOCK

def get_zdaemon_banlist_file():
    """Gets the full resolved path to the ZDaemon banlist file.

    :returns: the full resolved path to the ZDaemon master banlist
              file, properly parsed into ZDStack's banlist format
    :rtype: string

    """
    global ZDAEMON_BANLIST_FILE
    if not ZDAEMON_BANLIST_FILE:
        cp = get_configparser()
        bd = cp.getpath('DEFAULT', 'zdstack_master_banlist_file')
        ZDAEMON_BANLIST_FILE = bd
    return ZDAEMON_BANLIST_FILE

def get_zdaemon_banlist_data():
    """Gets the contents of the ZDaemon master banlist.

    :returns: the contents of the ZDaemon master banlist.
    :rtype: string

    """
    global URL_OPENER
    global ZDAEMON_BANLIST_URL
    url_fobj = URL_OPENER.open(ZDAEMON_BANLIST_URL)
    banlist_data = url_fobj.read()
    url_fobj.close()
    if banlist_data and len(banlist_data) > 200:
        ###
        # Not the best test, but whatever.
        ###
        return banlist_data
    else:
        e = ValueError("ZDaemon banlist data was malformed")
        e.banlist_data = banlist_data
        raise e

def get_rpc_server_class():
    """Gets the RPC server class.

    :rtype: either :class:`~ZDStack.RPCServer.XMLRPCServer` or
                   :class:`~ZDStack.RPCServer.JSONRPCServer`

    """
    global RPC_CLASS
    if not RPC_CLASS:
        cp = get_configparser()
        if cp.get('DEFAULT', 'zdstack_rpc_protocol') == 'xml-rpc':
            from ZDStack.RPCServer import XMLRPCServer
            RPC_CLASS = XMLRPCServer
        elif cp.get('DEFAULT', 'zdstack_rpc_protocol') == 'json-rpc':
            from ZDStack.RPCServer import JSONRPCServer
            RPC_CLASS = JSONRPCServer
    return RPC_CLASS

def get_rpc_proxy_class():
    """Gets the RPC proxy class.

    :rtype: either :class:`~ZDStack.RPCServer.XMLProxy` or
                   :class:`~ZDStack.RPCServer.JSONProxy`

    """
    global RPC_PROXY_CLASS
    if not RPC_PROXY_CLASS:
        cp = get_configparser()
        if cp.get('DEFAULT', 'zdstack_rpc_protocol') == 'xml-rpc':
            from ZDStack.RPCServer import XMLProxy
            RPC_PROXY_CLASS = XMLProxy
        elif cp.get('DEFAULT', 'zdstack_rpc_protocol') == 'json-rpc':
            from ZDStack.RPCServer import JSONProxy
            RPC_PROXY_CLASS = JSONProxy
        else:
            raise ValueError("Unsupported RPC protocol")
    return RPC_PROXY_CLASS

def get_json_module():
    """Gets the json module.

    :rtype: module
    :returns: either the json module included with Python 2.6, or the
              simplejson module.

    """
    global JSON_MODULE
    if not JSON_MODULE:
        raise JSONNotFoundError
    return JSON_MODULE

def get_server_proxy():
    """Gets a ZDStack server proxy.
    
    :rtype: an instance of either :class:`~ZDStack.RPCServer.XMLProxy`
                               or :class:`~ZDStack.RPCServer.JSONProxy`
    
    """
    cp = get_configparser() # assuming it's already loaded at this point
    address = 'http://%s:%s' % (cp.get('DEFAULT', 'zdstack_rpc_hostname'),
                                cp.get('DEFAULT', 'zdstack_port'))
    ZDSLOG.debug("%s(%s)" % (RPC_PROXY_CLASS, address))
    return get_rpc_proxy_class()(address)

def get_configparser(reload=False, raw=False, check=False):
    """Gets ZDStack's ConfigParser.

    :param reload: whether or not to reload the configuration file
    :type reload: boolean
    :param raw: disables value interpolation
    :type raw: boolean
    :param check: whether or not to check some files and folders for
                  existence, proper permissions, etc, defaults to False
    :type check: boolean
    :rtype: :class:`~ZDStack.ZDSConfigParser.ZDSConfigParser` or
            :class:`~ZDStack.ZDSConfigParser.RawZDSConfigParser`

    """
    if raw:
        return RCP(get_configfile())
    global CONFIGPARSER
    if CONFIGPARSER is None or reload:
        CONFIGPARSER = load_configparser(check=check)
    return CONFIGPARSER

def get_plugins(plugins='all'):
    """Gets the installed plugins.

    :param plugins: the names of the plugins to get, if 'all', returns
                    all plugins.
    :type plugins: list of strings or string
    :rtype: a list of modules

    """
    global PLUGINS
    if PLUGINS is None:
        cp = get_configparser()
        plugin_folder = cp.getpath('DEFAULT', 'zdstack_plugin_folder', False)
        if not plugin_folder:
            PLUGINS = []
        else:
            from ZDStack.Plugins import get_plugins
            PLUGINS = get_plugins(plugin_folder)
    return [x for x in PLUGINS if plugins == 'all' or x.__name__ in plugins]

def set_debugging(debugging):
    """Turns debugging on or off.
    
    :param debugging: whether or not debugging is enabled
    :type debugging: boolean
    
    """
    global DEBUGGING
    if DEBUGGING != debugging:
        needs_reloading = True
    else:
        needs_reloading = False
    DEBUGGING = debugging
    if needs_reloading:
        get_zdslog(reload=True)

def get_debugging():
    """Gets whether debugging is set or not.

    :rtype: boolean.

    """
    global DEBUGGING
    return DEBUGGING == True

def get_zdslog(reload=False):
    """Gets the ZDStack logger.

    :param reload: whether or not to reload the logger
    :type reload: boolean
    :rtype: Logger

    """
    global ZDSLOG
    global DEBUGGING
    if reload or isinstance(ZDSLOG, DummyLog):
        ZDSLOG = logging.getLogger('ZDStack')
        for handler in ZDSLOG.handlers:
            ZDSLOG.removeHandler(handler)
        cp = get_configparser()
        log_folder = cp.getpath('DEFAULT', 'zdstack_log_folder')
        log_file = os.path.join(log_folder, 'ZDStack.log')
        if DEBUGGING:
            log_level = logging.DEBUG
            sa_log_level = logging.DEBUG
            log_format = '[%(asctime)s] '
            log_format += '%(filename)-18s - %(funcName)-25s '
            log_format += '- %(lineno)-4d: '
            log_format += '%(levelname)-5s %(message)s'
            formatter = DebugFormatter(log_format, datefmt=DATEFMT)
        else:
            log_level = logging.INFO
            sa_log_level = logging.ERROR
            log_format = '[%(asctime)s] '
            log_format += '%(levelname)-8s %(message)s'
            formatter = logging.Formatter(log_format)
        h = TimedRotatingFileHandler(log_file, when='midnight', backupCount=4)
        h.setLevel(log_level)
        h.setFormatter(formatter)
        ZDSLOG.addHandler(h)
        ZDSLOG.setLevel(log_level)
        logging.getLogger('sqlalchemy.engine').addHandler(h)
        logging.getLogger('sqlalchemy.engine').setLevel(sa_log_level)
    return ZDSLOG

def initialize_database(do_not_map=False):
    """Initializes the Database.

    :param do_not_map: whether or not initialize_database() should map
                       classes to tables.
    :type do_not_map: boolean

    This *MUST* be called before running importing Stack, but can only
    be called AFTER initializing logging (set_debugging and all that).

    """
    zdslog = get_zdslog()
    zdslog.debug("Initializing Database")
    engine = get_engine()
    metadata = get_metadata()
    ###
    # Wow do I ever wish I could do from ZDStack.ZDSTables import * here.
    # Fuck!
    ###
    from ZDStack.ZDSTables import ports_and_gamemodes, rounds_and_aliases, \
                                  aliases_table, team_colors_table, \
                                  wads_table, maps_table, weapons_table, \
                                  ports_table, game_modes_table, \
                                  rounds_table, stored_players_table, \
                                  frags_table, flag_touches_table, \
                                  flag_returns_table, rcon_accesses_table, \
                                  rcon_actions_table, rcon_denials_table
    ###
    # Wow do I ever wish I could do from ZDStack.ZDSModels import * here.
    # Fuck!
    ###
    from ZDStack.ZDSModels import Alias, TeamColor, Wad, Map, Weapon, Port, \
                                  GameMode, Round, StoredPlayer, Frag, \
                                  FlagTouch, FlagReturn, RCONAccess, \
                                  RCONAction, RCONDenial, RoundsAndAliases
    if not do_not_map:
        ###
        # Parent cascades.
        ###
        _pc = 'save-update, delete, delete-orphan'
        mapper(Alias, aliases_table, properties={
         'rounds': relation(Round, secondary=rounds_and_aliases),
         'frags': relation(Frag, backref='fragger', cascade=_pc,
                       primaryjoin=frags_table.c.fragger_id==aliases_table.c.id),
         'deaths': relation(Frag, backref='fraggee', cascade=_pc,
                       primaryjoin=frags_table.c.fraggee_id==aliases_table.c.id),
         'flag_touches': relation(FlagTouch, backref='alias', cascade=_pc),
         'flag_returns': relation(FlagReturn, backref='alias', cascade=_pc),
         'rcon_accesses': relation(RCONAccess, backref='alias', cascade=_pc),
         'rcon_denials': relation(RCONDenial, backref='alias', cascade=_pc),
         'rcon_actions': relation(RCONAction, backref='alias', cascade=_pc)
        })
        mapper(TeamColor, team_colors_table, properties={
         'frags': relation(Frag, backref='fragger_team_color', cascade=_pc,
                           primaryjoin=frags_table.c.fragger_team_color_name==\
                                       team_colors_table.c.color),
         'deaths': relation(Frag, backref='fraggee_team_color', cascade=_pc,
                            primaryjoin=frags_table.c.fraggee_team_color_name==\
                                        team_colors_table.c.color),
         'flag_touches': relation(FlagTouch, backref='player_team_color',
                                  cascade=_pc),
         'flag_returns': relation(FlagReturn, backref='player_team_color',
                                  cascade=_pc)
        })
        mapper(Wad, wads_table, properties={
          'maps': relation(Map, order_by=maps_table.c.number, backref='wad')
        })
        mapper(Map, maps_table, properties={
         'rounds': relation(Round, backref='map', cascade=_pc)
        })
        mapper(Weapon, weapons_table, properties={
         'frags': relation(Frag, backref='weapon', cascade=_pc)
        })
        mapper(Port, ports_table, properties={
         'game_modes': relation(GameMode, secondary=ports_and_gamemodes)
        })
        mapper(GameMode, game_modes_table, properties={
         'ports': relation(Port, secondary=ports_and_gamemodes),
         'rounds': relation(Round, backref='game_mode', cascade=_pc)
        })
        mapper(Round, rounds_table, properties={
         'aliases': relation(Alias, secondary=rounds_and_aliases),
         'frags': relation(Frag, backref='round', cascade=_pc),
         'flag_touches': relation(FlagTouch, backref='round', cascade=_pc),
         'flag_returns': relation(FlagReturn, backref='round', cascade=_pc),
         'rcon_accesses': relation(RCONAccess, backref='round', cascade=_pc),
         'rcon_denials': relation(RCONDenial, backref='round', cascade=_pc),
         'rcon_actions': relation(RCONAction, backref='round', cascade=_pc)
        })
        mapper(RoundsAndAliases, rounds_and_aliases, properties={
          'alias': relation(Alias),
          'round': relation(Round),
          'player': relation(StoredPlayer, backref='rounds_and_aliases',
            primaryjoin=rounds_and_aliases.c.alias_id == aliases_table.c.id,
            secondary=aliases_table,
            secondaryjoin=and_(aliases_table.c.stored_player_name == \
                                 stored_players_table.c.name),
            viewonly=True)
        })
        mapper(StoredPlayer, stored_players_table, properties={
         'aliases': relation(Alias, backref='stored_player'),
        })
        mapper(Frag, frags_table)
        mapper(FlagTouch, flag_touches_table)
        mapper(FlagReturn, flag_returns_table)
        mapper(RCONAccess, rcon_accesses_table)
        mapper(RCONDenial, rcon_denials_table)
        mapper(RCONAction, rcon_actions_table)
    zdslog.debug("Creating tables")
    metadata.create_all(engine)
    zdslog.debug("Initializing Database Data")
    from ZDStack.ZDSDatabaseData import insert_initial_data
    session = get_session_class()()
    # try:
    #     session.begin()
    #     existing_colors = [x.color for x in session.query(TeamColor).all()]
    #     for color in [x for x in TEAM_COLORS if x not in existing_colors]:
    #         tc = TeamColor()
    #         tc.color = color
    #         session.add(tc)
    #     session.commit()
    # except:
    #     session.rollback()
    #     raise
    # session = get_session_class()()
    try:
        session.begin()
        insert_initial_data(session)
        session.commit()
    except IntegrityError:
        zdslog.info('Database already contains initial data, skipping')
        session.rollback()
    except:
        session.rollback()
        raise

# set_debugging(False)

