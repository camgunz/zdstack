import os.path
import urllib
import socket
from ConfigParser import RawConfigParser as RCP

__host, __aliases, __addresses = socket.gethostbyaddr(socket.gethostname())
__hostnames = [x for x in [__host] + __aliases if '.' in x]
if not __hostnames:
    raise Exception("Could not obtain the Fully Qualified Hostname")

CONFIGPARSER = None

HOSTNAME = __hostnames[0]
SERVICE_ADMIN_SERVER = "totaltrash.org" # put server address (not URL) of admin server here
SERVICE_PASSWORD = "thatimnotnocow" # put password here
BASE_SERVICE_URL = 'http://%s/services/%%s/%%s' % (SERVICE_ADMIN_SERVER)

ZSERV_EXE = '/root/bin/zserv'

def yes(x):
    return x.lower() in ('y', 'yes', 't', 'true', '1', 'on', 'absolutely')

def no(x):
    return x.lower() in ('n', 'no', 'f', 'false', '0', 'off', 'never')

def get_service_info(info, service, address):
    url = BASE_SERVICE_URL % (urllib.quote(info), urllib.quote(service))
    return urllib.urlopen(url).read()

def send_service_action(action, service, address, type):
    params = {'service_address': address, 'authentication': SERVICE_PASSWORD}
    url = BASE_SERVICE_URL % (urllib.quote(action), urllib.quote(service))
    return urllib.urlopen(url, urllib.urlencode(params)).read()

def timedelta_in_seconds(x):
    return (x.days * 86400) + x.seconds

def get_configparser(config_file=None):
    global CONFIGPARSER
    global SERVICE_ADMIN_SERVER
    global SERVICE_PASSWORD
    global SERVICE_URL_PATH
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
    if 'service_admin_server' not in CONFIGPARSER.defaults():
        raise ValueError("Option 'service_admin_server' not found")
    if 'service_password' not in CONFIGPARSER.defaults():
        raise ValueError("Option 'service_password' not found")
    if 'service_url_path' not in CONFIGPARSER.defaults():
        raise ValueError("Option 'service_url_path' not found")
    SERVICE_ADMIN_SERVER = CONFIGPARSER.defaults()['service_admin_server']
    SERVICE_PASSWORD = CONFIGPARSER.defaults()['service_password']
    SERVICE_URL_PATH = CONFIGPARSER.defaults()['service_url_path']
    return CONFIGPARSER

def rotate_log(self, log_path):
    log_dir, log_file = (os.path.dirname(log_path), os.path.basename(log_path))
    tokens = [x for x in log_file.split('.') if x]
    if not tokens:
        raise ValueError("Invalid log filename format")
    if not tokens[-1].isnum():
        log_file += '.1'
    else:
        log_file = log_file.replace('.' + tokens[-1],
                                    '.' + str(int(tokens[-1]) + 1))
