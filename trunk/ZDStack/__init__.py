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

__host, __aliases, __addresses = socket.gethostbyaddr(socket.gethostname())
__hostnames = [x for x in [__host] + __aliases if '.' in x]
if not __hostnames:
    raise Exception("Could not obtain the Fully Qualified Hostname")

__all__ = ['HOSTNAME', 'CONFIGPARSER', 'ZSERV_EXE', 'DATABASE', 'LOGFILE',
           'DEBUGGING', 'LOGGER', 'TRACER', 'PLUGINS', 'DATEFMT', 'get_logger',
           'load_configparser', 'get_configparser', 'get_zserv_exe',
           'get_database', 'get_plugins', 'set_debugging', 'log']

HOSTNAME = __hostnames[0]
CONFIGFILE = None
CONFIGPARSER = None
ZSERV_EXE = None
DATABASE = None
LOGFILE = None
DEBUGGING = None
PLUGINS = None
DATEFMT = '%Y-%m-%d %H:%M:%S'

class PlayerNotFoundError(Exception):

    def __init__(self, name=None, ip_address_and_port=None):
        if not name and not ip_address_and_port:
            es = "PlayerNotFoundError requires either a name or an"
            es += "('ip_address', port)"
            raise ValueError(es)
        self.name = name
        self.ip_address_and_port = ip_address_and_port
        self.ip_address, self.port = self.ip_address_and_port
        if name:
            Exception.__init__(self, "Player [%s] not found" % (name))
        else:
            es = "Player Address [%s:%s] not found"
            Exception.__init__(self, es % ip_address_and_port)

class DebugTRFH(logging.handlers.TimedRotatingFileHandler):
    def emit(self, record):
        logging.handlers.TimedRotatingFileHandler.emit(self, record)
        print >> sys.stderr, record.getMessage().strip()

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

def get_database(config_file=None):
    global CONFIGPARSER
    global DATABASE
    if DATABASE is None and 'database_folder' in CONFIGPARSER.defaults():
        if CONFIGPARSER is None:
            get_configparser(config_file)
        database_folder = CONFIGPARSER.defaults()['database_folder']
        if not os.path.isdir(database_folder):
            try:
                os.mkdir(database_folder)
            except OSError:
                es = "Database folder [%s] not found"
                raise ValueError(es % (database_folder))
        try:
            from PyXSE.Database import Database, TableNotFoundError
            DATABASE = Database(database_folder)
        except ImportError, e:
            return None
        try:
            DATABASE.get_table('players')
        except TableNotFoundError:
            DATABASE.create_table('players', ['name', 'addresses'],
                                             ['str', 'str'], ['name'])
    return DATABASE

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

