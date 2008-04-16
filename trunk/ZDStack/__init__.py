import os
import re
import urllib
import socket

from threading import Thread
from ConfigParser import RawConfigParser as RCP

from pyfileutils import read_file

__host, __aliases, __addresses = socket.gethostbyaddr(socket.gethostname())
__hostnames = [x for x in [__host] + __aliases if '.' in x]
if not __hostnames:
    raise Exception("Could not obtain the Fully Qualified Hostname")

__all__ = ['HOSTNAME', 'CONFIGPARSER', 'ZSERV_EXE', 'DATABASE', 'yes', 'no',
           'timedelta_in_seconds', 'start_thread', 'load_configparser',
           'get_configparser', 'get_zserv_exe', 'get_database']

HOSTNAME = __hostnames[0]
CONFIGPARSER = None
ZSERV_EXE = None
DATABASE = None

def yes(x):
    return x.lower() in ('y', 'yes', 't', 'true', '1', 'on', 'absolutely')

def no(x):
    return x.lower() in ('n', 'no', 'f', 'false', '0', 'off', 'never')

def timedelta_in_seconds(x):
    return (x.days * 86400) + x.seconds

def start_thread(target, daemonic=True):
    t = Thread(target=target)
    t.setDaemon(daemonic)
    t.start()
    return t

def resolve_file(f):
    return os.path.abspath(os.path.expanduser(f))

def get_configparser(config_file=None, reload=False):
    global CONFIGPARSER
    if reload or (CONFIGPARSER is None):
        CONFIGPARSER = load_configparser(config_file)
    return CONFIGPARSER

def load_configparser(config_file=None):
    cp = RCP()
    if config_file is not None:
        config_file = resolve_file(config_file)
        if not os.path.isfile(config_file):
            es = "Could not find configuration file [%s]"
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
    config_fobj = open(config_file)
    regexp = r'^\[(.*)\]%'
    sections = []
    for line in config_fobj.read().splitlines():
        if re.match(regexp, line) and line in sections:
            es = "Duplicate section found in config: [%s]"
            raise ValueError(es % (line))
    config_fobj.seek(0)
    cp.readfp(config_fobj)
    cp.filename = config_file
    return cp

def get_zserv_exe(config_file=None):
    global CONFIGPARSER
    global ZSERV_EXE
    if CONFIGPARSER is None:
        get_configparser(config_file)
    if ZSERV_EXE is None:
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
    if CONFIGPARSER is None:
        get_configparser(config_file)
    if DATABASE is None and 'database_folder' in CONFIGPARSER.defaults():
        database_folder = CONFIGPARSER.defaults()['database_folder']
        if not os.path.isdir(database_folder):
            try:
                os.mkdir(database_folder)
            except OSError:
                es = "Could not find database folder [%s]"
                raise ValueError(es % (database_folder))
        try:
            from PyXSE.Database import Database, TableNotFoundError
            DATABASE = Database(database_folder)
            try:
                DATABASE.get_table('players')
            except TableNotFoundError:
                DATABASE.create_table('players', ['name', 'addresses'],
                                      ['str', 'str'], ['name'])
        except ImportError, e:
            raise # for debugging
            pass
    return DATABASE

