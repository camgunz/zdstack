import os
import re
import time
import urllib
import socket
import logging

from datetime import datetime, timedelta
from threading import Thread
from cStringIO import StringIO
from logging.handlers import TimedRotatingFileHandler

from pyfileutils import read_file, append_file

from ZDStack.Utils import resolve_file
from ZDStack.ConfigParser import ConfigParser as CP

__host, __aliases, __addresses = socket.gethostbyaddr(socket.gethostname())
__hostnames = [x for x in [__host] + __aliases if '.' in x]
if not __hostnames:
    raise Exception("Could not obtain the Fully Qualified Hostname")

__all__ = ['HOSTNAME', 'CONFIGPARSER', 'ZSERV_EXE', 'DATABASE', 'LOGFILE',
           'DEBUGGING', 'LOGGER', 'TRACER', 'PLUGINS', 'DATEFMT', 'get_logger',
           'load_configparser', 'get_configparser', 'get_zserv_exe',
           'get_database', 'get_logfile', 'get_plugins', 'get_tracer',
           'set_debugging', 'log', 'debug']

HOSTNAME = __hostnames[0]
CONFIGPARSER = None
ZSERV_EXE = None
DATABASE = None
LOGFILE = None
DEBUGGING = None
LOGGER = None
TRACER = None
PLUGINS = None
DATEFMT = '%Y/%m/%d %H:%M:%S'

logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] %(levelname)-8s %(message)s',
                    datefmt=DATEFMT,
                    filename='/dev/null')

def get_configparser(config_file=None, reload=False):
    global CONFIGPARSER
    if reload or (CONFIGPARSER is None):
        CONFIGPARSER = load_configparser(config_file)
    return CONFIGPARSER

def load_configparser(config_file=None):
    cp = CP()
    if config_file is not None:
        config_file = resolve_file(config_file)
        if not os.path.isfile(config_file):
            es = "Configuration file [%s] not found"
            raise ValueError(es % (config_file))
    else:
        possible_config_files = ['zdstackrc', 'zdstack.ini',
                                 '~/.zdstackrc', '~/.zdstack.ini',
                                 '~/.zdstack/zdstackrc',
                                 '~/.zdstack/zdstack.ini',
                                 '/etc/zdstackrc', '/etc/zdstack.ini',
                                 '/etc/zdstack/zdstackrc'
                                 '/etc/zdstack/zdstack.ini']
        possible_config_files = \
                        [resolve_file(x) for x in possible_config_files]
        if not [y for y in possible_config_files if os.path.isfile(y)]:
            raise ValueError("Could not find a valid configuration file")
        config_file = possible_config_files[0]
    config_fobj = StringIO(read_file(config_file))
    sections = []
    for line in config_fobj.getvalue().splitlines():
        if re.match(cp.SECTCRE, line):
            if line in sections:
                es = "Duplicate section found in config: [%s]"
                raise ValueError(es % (line))
            else:
                sections.append(line)
    config_fobj.seek(0)
    cp.readfp(config_fobj)
    cp.filename = config_file
    for section in cp.sections():
        cp.set(section, 'name', section)
    cp.file = config_file
    return cp

def get_zserv_exe(config_file=None):
    global CONFIGPARSER
    global ZSERV_EXE
    if ZSERV_EXE is None:
        if CONFIGPARSER is None:
            get_configparser(config_file)
        if 'zserv_exe' not in CONFIGPARSER.defaults():
            raise ValueError("Option 'zserv_exe' not found")
        else:
            zserv_exe = CONFIGPARSER.defaults()['zserv_exe']
            zserv_exe = os.path.expanduser(zserv_exe)
            zserv_exe = os.path.abspath(zserv_exe)
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
        if not os.path.isdir(resolve_dir(plugin_dir)):
            raise ValueError("Plugin folder [%s] not found" % (plugin_dir))
        from ZDStack.Plugins import get_plugins
        PLUGINS = get_plugins(plugin_dir)
    return [x for x in PLUGINS if plugins == 'all' or x.__name__ in plugins]

def get_logfile(config_file=None):
    global CONFIGPARSER
    global LOGFILE
    if LOGFILE is None:
        if CONFIGPARSER is None:
            get_configparser(config_file)
        LOGFILE = os.path.join(CONFIGPARSER.defaults()['rootfolder'],
                               'ZDStack.log')
    return LOGFILE

def _get_trfh(level, log_string, config_file=None):
    global LOGFILE
    global LOGGER
    if LOGGER is None:
        if LOGFILE is None:
            get_logfile(config_file)
    logger = TimedRotatingFileHandler(LOGFILE, when='midnight', backupCount=4)
    formatter = logging.Formatter(fmt=log_string, datefmt=DATEFMT)
    logger.setLevel(level)
    logger.setFormatter(formatter)
    return logger

def get_logger(config_file=None):
    global LOGGER
    if LOGGER is None:
        format='[%(asctime)s] %(levelname)-8s %(message)s'
        LOGGER = _get_trfh(logging.INFO, format, config_file)
    return LOGGER

def get_tracer(config_file=None):
    global TRACER
    if TRACER is None:
        format='[%(asctime)s] %(module)s:%(lineno)d %(message)s'
        TRACER = _get_trfh(logging.INFO, format, config_file)
    return TRACER

def set_debugging(debugging):
    global DEBUGGING
    DEBUGGING = debugging
    if debugging:
        logging.getLogger('').removeHandler(get_logger())
        logging.getLogger('').addHandler(get_tracer())
    else:
        logging.getLogger('').removeHandler(get_tracer())
        logging.getLogger('').addHandler(get_logger())

def log(s):
    logging.getLogger('').info(s)

def debug(s=''):
    logging.getLogger('').debug(s)

