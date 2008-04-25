import os
import re
import time
import urllib
import socket

from datetime import datetime, timedelta
from threading import Thread
from cStringIO import StringIO
from ConfigParser import ConfigParser as CP

from pyfileutils import read_file, append_file

__host, __aliases, __addresses = socket.gethostbyaddr(socket.gethostname())
__hostnames = [x for x in [__host] + __aliases if '.' in x]
if not __hostnames:
    raise Exception("Could not obtain the Fully Qualified Hostname")

__all__ = ['HOSTNAME', 'CONFIGPARSER', 'ZSERV_EXE', 'DATABASE', 'yes', 'no',
           'timedelta_in_seconds', 'start_thread', 'load_configparser',
           'get_configparser', 'get_zserv_exe', 'get_database',
           'get_logfile_suffix', 'resolve_file', 'log', 'homogenize',
           'parse_player_name', 'html_escape']

HOSTNAME = __hostnames[0]
CONFIGPARSER = None
ZSERV_EXE = None
DATABASE = None
LOGFILE = None

def yes(x):
    return x.lower() in ('y', 'yes', 't', 'true', '1', 'on', 'absolutely')

def no(x):
    return x.lower() in ('n', 'no', 'f', 'false', '0', 'off', 'never')

def timedelta_in_seconds(x):
    return (x.days * 86400) + x.seconds

def start_thread(target, name=None, daemonic=True):
    log("Starting thread [%s]" % (name))
    t = Thread(target=target, name=name)
    t.setDaemon(daemonic)
    t.start()
    return t

def get_logfile_suffix(roll=False):
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)
    if roll and now.hour == 23:
        today += timedelta(days=1)
    return today.strftime('-%Y%m%d') + '.log'

def resolve_file(f):
    return os.path.abspath(os.path.expanduser(f))

def log(x):
    # return # to be fully re-implemented using the Logging module
    append_file('[%s] %s\n' % (time.ctime(), x), get_logfile(), overwrite=True)

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
    config_fobj = StringIO(read_file(config_file))
    regexp = r'^\[(.*)\]%'
    sections = []
    for line in config_fobj.getvalue().splitlines():
        if re.match(regexp, line) and line in sections:
            es = "Duplicate section found in config: [%s]"
            raise ValueError(es % (line))
    config_fobj.seek(0)
    cp.readfp(config_fobj)
    cp.filename = config_file
    for section in cp.sections():
        cp.set(section, 'name', section)
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

def get_logfile(config_file=None):
    global CONFIGPARSER
    global LOGFILE
    if CONFIGPARSER is None:
        get_configparser(config_file)
    if LOGFILE is None:
        LOGFILE = os.path.join(CONFIGPARSER.defaults()['rootfolder'],
                               'ZDStack.log')
    return LOGFILE

def homogenize(s):
    return s.replace(' ', '').lower().replace('\n', '').replace('\t', '')

def parse_player_name(name):
    ###
    # It's a little ridiculous, but people are VERY creative in how they
    # add their clan/team tags.  So we have a ridiculous algorithm to
    # figure this out.
    ###
    from ZDStack.Token import Token

    delimiters = {'[': ']', '<': '>', '(': ')', '*': '*', '_': '_',
                  '-': '-', ']': '[', '>': '<', ')': '('}
    seen = []
    waiting = []
    tokens = []
    s = ''
    other_stuff = ''
    in_token = False
    for c in name:
        if c in delimiters.keys(): # found a delimiter
            if waiting and waiting[-1] == c: # found the end of a token
                tokens.append(Token(s, seen[-1], c))
                s = ''
                waiting = waiting[:-1]
                seen = seen[:-1]
                in_token = False
            elif in_token: # found the beginning of a new token
                tokens.append(Token(s, seen[-1]))
                waiting = waiting[:-1]
                seen = seen[:-1]
                seen.append(c)
                s = ''
            else: # found the beginning of a token
                waiting = waiting[:-1]
                seen = seen[:-1]
                seen.append(c)
                waiting.append(delimiters[c])
                # other_stuff += c
                in_token = True
        elif in_token: # add to the current token
            s += c
        else: # not a token
            other_stuff += c
    if s:
        if in_token:
            tokens.append(Token(s, ''.join(seen)))
        else:
            other_stuff += s
    try:
        tokens = sorted([(len(t), t) for t in tokens])
        # tokens.reverse()
        token = tokens[0][1]
        tag = str(token)
        return (tag, name.replace(tag, ''))
    except IndexError: # no tag
        return (None, name)

def html_escape(s):
    # Basically ripped from web.py
    t = s.replace('&', "&amp;")
    t = t.replace('<', "&lt;")
    t = t.replace('>', "&gt;")
    t = t.replace("'", "&#39;")
    t = t.replace('"', "&quot;")
    return t

