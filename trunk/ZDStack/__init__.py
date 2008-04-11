import os
import urllib
import socket
from ConfigParser import RawConfigParser as RCP

__host, __aliases, __addresses = socket.gethostbyaddr(socket.gethostname())
__hostnames = [x for x in [__host] + __aliases if '.' in x]
if not __hostnames:
    raise Exception("Could not obtain the Fully Qualified Hostname")

__all__ = ['HOSTNAME', 'CONFIGPARSER', 'ZSERV_EXE', 'DATABASE', 'yes', 'no',
           'timedelta_in_seconds', 'get_configparser']

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

def get_configparser(config_file=None):
    global CONFIGPARSER
    global ZSERV_EXE
    global DATABASE
    if CONFIGPARSER is None:
        cp = RCP()
        if config_file is not None:
            if not os.path.isfile(config_file):
                es = "Could not find configuration file [%s]"
                raise ValueError(es % (config_file))
        else:
            possible_config_files = ['zdstack.ini', '~/.zdstack/zdstack.ini',
                                     '/etc/zdstack/zdstack.ini']
            possible_config_files = [x for x in possible_config_files \
                                                        if os.path.isfile(x)]
            if not possible_config_files:
                raise ValueError("Could not find a valid configuration file")
            else:
                config_file = possible_config_files[0]
        cp.read(config_file)
        cp.filename = config_file
        CONFIGPARSER = cp
    return CONFIGPARSER

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
            print "Importing PyXSE stuff"
            from PyXSE.Database import Database, TableNotFoundError
            DATABASE = Database(database_folder)
            try:
                DATABASE.get_table('players')
            except TableNotFoundError:
                DATABASE.create_table('players', ['name', 'addresses'],
                                      ['str', 'str'], ['name'])
            print "Done with imports"
        except ImportError, e:
            raise # for debugging
            pass
    return DATABASE

