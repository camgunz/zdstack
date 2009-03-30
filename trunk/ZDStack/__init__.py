import os
import re
import sys
import time
import urllib
import socket
import logging
import logging.handlers

from decimal import Decimal
from datetime import datetime, timedelta
from threading import Thread
from cStringIO import StringIO

from pyfileutils import read_file, append_file

from ZDStack.Utils import resolve_path
from ZDStack.ZDSConfigParser import ZDSConfigParser as CP

__all__ = ['SUPPORTED_ENGINE_TYPES', 'HOSTNAME', 'LOOPBACK', 'CONFIGFILE',
           'CONFIGPARSER', 'DATABASE', 'DEBUGGING' 'PLUGINS', 'DATEFMT',
           'DB_ENGINE', 'DB_METADATA', 'DB_SESSION_CLASS', 'RPC_CLASS',
           'RPC_PROXY_CLASS', 'TEAM_COLORS', 'TICK', 'MAX_TIMEOUT',
           'DIE_THREADS_DIE', 'PlayerNotFoundError', 'TeamNotFoundError',
           'ZServNotFoundError', 'DebugTRFH', 'get_hostname', 'get_loopback',
           'get_engine', 'get_metadata', 'get_session_class', 'get_session',
           'get_configfile', 'set_configfile', 'load_configparser',
           'get_configparser', 'get_server_proxy', 'get_plugins',
           'set_debugging', 'log']

REQUIRED_GLOBAL_CONFIG_OPTIONS = \
    ('zdstack_username', 'zdstack_password', 'zdstack_port',
     'zdstack_rpc_protocol', 'zdstack_log_folder', 'zdstack_pid_file',
     'zdstack_zserv_folder', 'zdstack_plugin_folder', 'zdstack_iwad_folder',
     'zdstack_wad_folder')

REQUIRED_SERVER_CONFIG_OPTIONS = \
    ('zserv_exe', 'iwad', 'enable_events', 'enable_stats', 'enable_plugins',
     'hostname', 'admin_email', 'website', 'motd', 'advertise', 'skill',
     'mode', 'port')

REQUIRED_GLOBAL_VALID_FOLDERS = \
    (('zdstack_log_folder', os.R_OK | os.W_OK | os.X_OK),
     ('zdstack_zserv_folder', os.R_OK | os.W_OK | os.X_OK),
     ('zdstack_plugin_folder', os.R_OK | os.X_OK),
     ('zdstack_iwad_folder', os.R_OK | os.X_OK),
     ('zdstack_wad_folder', os.R_OK | os.X_OK))

REQUIRED_SERVER_VALID_FILES = \
    (('zserv_exe', os.R_OK | os.X_OK), ('iwad', os.R_OK))

SUPPORTED_ENGINE_TYPES = \
    ('sqlite', 'postgres', 'mysql', 'oracle', 'mssql', 'firebird')

SUPPORTED_GAME_MODES = ('ctf', 'coop', 'duel', 'ffa', 'teamdm')

HOSTNAME = None
LOOPBACK = None
CONFIGFILE = None
CONFIGPARSER = None
DATABASE = None
DEBUGGING = None
PLUGINS = None
DATEFMT = '%Y-%m-%d %H:%M:%S'
DB_ENGINE = None
DB_METADATA = None
DB_SESSION_CLASS = None
RPC_CLASS = None
RPC_PROXY_CLASS = None
TEAM_COLORS = ('red', 'blue', 'green', 'white')
TICK = Decimal('0.027')
MAX_TIMEOUT = 1
DIE_THREADS_DIE = False

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

class TeamNotFoundError(Exception):

    def __init__(self, color):
        Exception.__init__(self, "%s Team not found" % (color.capitalize()))

class ZServNotFoundError(Exception):

    def __init__(self, zserv_name:
        Exception.__init__(self, "ZServ [%s] not found" % (zserv_name))

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
    global DB_ENGINE
    if not DB_ENGINE:
        d = get_configparser().defaults()
        db_driver = d.get('zdstack_database_engine', 'sqlite').lower()
        if db_driver not in SUPPORTED_ENGINE_TYPES:
            raise ValueError("DB engine %s is not supported" % (db_driver))
        if db_driver == 'sqlite':
            db_name = d.get('zdstack_database_name', ':memory:')
            if db_name == ':memory:':
                db_str = 'sqlite://:memory:'
            else:
                db_name = resolve_path(db_name) # just to be sure
                if not os.path.isfile(db_name):
                    es = "SQLite DB file %s not found, will create new DB"
                    logging.info(es)
                db_str = 'sqlite:///%s' % (db_name)
        else:
            db_host = d['zdstack_database_host']
            if 'port' in d and d['port']:
                db_port = d['port']
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
            ###
            # Some databases might be configured for user-less/password-less
            # access (potentially dumb, but w/e).
            ###
            db_user = ''
            db_pass = ''
            ###
            # Be a little flexible in the labeling of the db user & pw fields
            ###
            if 'zdstack_database_user' in d and d['zdstack_database_user']:
                db_user = d['zdstack_database_user']
            elif 'zdstack_database_username' in d and \
               d['zdstack_database_username']:
                db_user = d['zdstack_database_username']
            if 'zdstack_database_pass' in d and d['zdstack_database_pass']:
                db_pass = d['zdstack_database_pass']
            elif 'zdstack_database_password' in d and \
               d['zdstack_database_password']:
                db_pass = d['zdstack_database_password']
            elif 'zdstack_database_passwd' in d and \
               d['zdstack_database_passwd']:
                db_pass = d['zdstack_database_passwd']
            db_str = db_temp % (db_driver, db_user, db_pass, db_host, db_name)
        from sqlalchemy import create_engine
        if db_driver == 'mysql':
            ###
            # We need to recycle connections every hour or so to avoid MySQL's
            # idle connection timeouts.
            ###
            logging.debug("Creating engine from DB str: [%s]" % (db_str))
            print "Creating engine from DB str: [%s]" % (db_str)
            DB_ENGINE = create_engine(db_str, pool_recycle=3600)
        else:
            logging.debug("Creating engine from DB str: [%s]" % (db_str))
            print "Creating engine from DB str: [%s]" % (db_str)
            DB_ENGINE = create_engine(db_str)
    return DB_ENGINE

def get_metadata():
    global DB_METADATA
    if not DB_METADATA:
        from sqlalchemy import MetaData
        DB_METADATA = MetaData()
        DB_METADATA.bind = get_engine()
    return DB_METADATA

def get_session_class():
    global DB_SESSION_CLASS
    if not DB_SESSION_CLASS:
        from sqlalchemy.orm import sessionmaker
        DB_SESSION_CLASS = sessionmaker(bind=get_engine())
    return DB_SESSION_CLASS

def get_session():
    Session = get_session_class()
    return Session()

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
                        [resolve_path(x) for x in possible_config_files]
        possible_config_files = \
                        [x for x in possible_config_files if os.path.isfile(x)]
        if not possible_config_files:
            raise ValueError("Could not find a valid configuration file")
        CONFIGFILE = possible_config_files[0]
    return CONFIGFILE

def set_configfile(config_file):
    global CONFIGFILE
    config_file = resolve_path(config_file)
    if not os.path.isfile(config_file):
        es = "Configuration file [%s] not found"
        raise ValueError(es % (config_file))
    CONFIGFILE = config_file

def load_configparser():
    global RPC_CLASS
    global RPC_PROXY_CLASS
    cp = CP(get_configfile(), allow_duplicate_sections=False)
    defaults = cp.defaults()
    for section in cp.sections():
        cp.set(section, 'name', section)
    for x in REQUIRED_GLOBAL_CONFIG_OPTIONS:
        if x not in defaults or not defaults[x]:
            raise ValueError("Required global option %s not found" % (x))
    for fo, m in REQUIRED_GLOBAL_VALID_FOLDERS:
        f = resolve_path(defaults[fo])
        if not os.path.isdir(f):
            raise ValueError("Required folder %s not found" % (fo))
        if not os.access(f, m):
            raise ValueError("Insufficient access provided for %s" % (f))
        cp.set('DEFAULT', fo, f)
    for s in cp.sections():
        d = dict(cp.items(s))
        for x in REQUIRED_SERVER_CONFIG_OPTIONS:
            if x not in d or not d[x]:
                es = "Required server option %s not found for server [%s]"
                raise ValueError(es % (x, s))
        for fo, m in REQUIRED_SERVER_VALID_FILES:
            f = resolve_path(cp.get(s, fo))
            if not os.access(f, m):
                raise ValueError("Insufficient access provided for %s" % (f))
            cp.set(s, fo, f)
        if d['mode'].lower() not in SUPPORTED_GAME_MODES:
            raise ValueError("Unsupported game mode %s" % (d['mode']))
    ###
    # Because we might have changed things, reload defaults
    ###
    defaults = cp.defaults()
    ###
    # Below are some checks for specific options & values
    ###
    ###
    # Check RPC protocol is supported
    ###
    rp = defaults['zdstack_rpc_protocol'].lower()
    if rp in ('jsonrpc', 'json-rpc'):
        cp.set('DEFAULT', 'zdstack_rpc_protocol', 'json-rpc')
        from ZDStack.RPCServer import JSONRPCServer
        from jsonrpc import ServiceProxy
        rpc_class = JSONRPCServer
        proxy_class = ServiceProxy
    elif rp in ('xmlrpc', 'xml-rpc'):
        cp.set('DEFAULT', 'zdstack_rpc_protocol', 'xml-rpc')
        from ZDStack.RPCServer import XMLRPCServer
        from xmlrpclib import ServerProxy
        rpc_class = XMLRPCServer
        proxy_class = ServerProxy
    else:
        es = "RPC Protocol [%s] not supported"
        raise ValueError(es % (defaults['zdstack_rpc_protocol']))
    ###
    # Resolve RPC hostname.
    ###
    if not 'zdstack_rpc_hostname' in defaults or \
       not defaults['zdstack_rpc_hostname'] or \
           defaults['zdstack_rpc_hostname'].lower() == 'localhost':
        cp.set('DEFAULT', 'zdstack_rpc_protocol', get_loopback())
    ###
    # Make sure the folder for the zserv processes exists.
    ###
    if not os.path.isdir(defaults['zdstack_zserv_folder']):
        try:
            os.mkdir(defaults['zdstack_zserv_folder'])
        except Exception, e:
            es = "Error: ZServ Server folder %s is not valid: %s"
            raise ValueError(es % (defaults['zdstack_zserv_folder'], e))
    ###
    # Resolve the PID file location.
    ###
    cp.set('DEFAULT', 'zdstack_pid_file',
           resolve_path(defaults['zdstack_pid_file']))
    RPC_CLASS = rpc_class
    RPC_PROXY_CLASS = proxy_class
    return cp

def get_configparser(reload=False):
    global CONFIGPARSER
    if CONFIGPARSER is None or reload:
        CONFIGPARSER = load_configparser()
    return CONFIGPARSER

def get_server_proxy():
    """Returns an object that is a proxy for the running ZDStack."""
    cp = get_configparser() # assuming it's already loaded at this point
    defaults = cp.defaults()
    address = 'http://%s:%s' % (defaults['zdstack_rpc_hostname'],
                                defaults['zdstack_port'])
    return RPC_PROXY_CLASS(address)

def get_plugins(plugins='all', config_file=None):
    global CONFIGPARSER
    global PLUGINS
    if PLUGINS is None:
        if CONFIGPARSER is None:
            get_configparser(config_file)
        d = CONFIGPARSER.defaults()
        if not 'plugin_folder' in d:
            PLUGINS = []
        plugin_folder = d['plugin_folder']
        if not os.path.isdir(resolve_path(plugin_folder)):
            raise ValueError("Plugin folder [%s] not found" % (plugin_folder))
        from ZDStack.Plugins import get_plugins
        PLUGINS = get_plugins(plugin_folder)
    return [x for x in PLUGINS if plugins == 'all' or x.__name__ in plugins]

def set_debugging(debugging, log_file=None, config_file=None):
    global DEBUGGING
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
    cp = get_configparser()
    log_folder = cp.defaults()['zdstack_log_folder']
    log_file = os.path.join(log_folder, 'ZDStack.log')
    formatter = logging.Formatter(__log_format, DATEFMT)
    handler = __handler_class(log_file, when='midnight', backupCount=4)
    handler.setFormatter(formatter)
    logging.RootLogger.root.addHandler(handler)
    logging.RootLogger.root.setLevel(__log_level)
    handler.setLevel(__log_level)

# set_debugging(False)

