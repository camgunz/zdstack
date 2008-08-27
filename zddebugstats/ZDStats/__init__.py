import os
from ConfigParser import RawConfigParser as RCP

import web

__all__ = ['get_config', 'get_server', 'RENDER', 'render_main', 'SERVER_IP']

__CONFIG = None
__SERVER = None
RENDER = None
SERVER_IP = None

def get_config(config_file=None):
    global __CONFIG
    global RENDER
    global SERVER_IP
    if not __CONFIG:
        if config_file:
            if not os.path.isfile(config_file):
                es = "Specified configuration file [%s] is not a file"
                raise ValueError(es % (config_file))
        else:
            possible_config_files = \
                [
                 os.path.join(os.getcwd(), 'zdwebstatsrc'),
                 os.path.join(os.getcwd(), 'zdwebstats.ini'),
                 os.path.expanduser('~/.zdwebstatsrc'),
                 os.path.expanduser('~/.zdwebstats.ini'),
                 os.path.expanduser('~/.zdwebstats/zdwebstatsrc'),
                 os.path.expanduser('~/.zdwebstats/zdwebstats.ini'),
                 '/etc/zdwebstatsrc',
                 '/etc/zdwebstats.ini',
                 '/etc/zdwebstats/zdwebstatsrc',
                 '/etc/zdwebstats/zdwebstats.ini'
                ]
            config_files = [x for x in possible_config_files if os.path.isfile(x)]
            if not config_files:
                raise RuntimeError("Could not find a suitable configuration file")
            config_file = config_files[0]
        cp = RCP()
        cp.read(config_file)
        config = cp.defaults()
        if not 'zdstack_address' in config:
            raise ValueError("Option [zdstack_address] not found in config")
        if not 'zdstack_protocol' in config:
            raise ValueError("Option [zdstack_protocol] not found in config")
        elif not config['zdstack_protocol'].lower() in \
                                    ['xmlrpc', 'jsonrpc', 'xml-rpc', 'json-rpc']:
            es = "ZDStack protocol [%s] is unsupported"
            raise ValueError(es % (config['zdstack_protocol']))
        if not 'zdstack_username' in config:
            raise ValueError("Option [zdstack_username] not found in config")
        if not 'zdstack_password' in config:
            raise ValueError("Option [zdstack_password] not found in config")
        if not 'server_ip' in config:
            raise ValueError("Option [server_ip] not found in config")
        if not 'base_url' in config:
            raise ValueError("Option [base_url] not found in config")
        elif not (config['base_url'].startswith('http://') or
                  config['base_url'].startswith('/')):
            raise ValueError("Option [base_url] is malformed, it must start with either a '/' or a 'http://'")
        else:
            config['base_url'] = config['base_url'].rstrip('/')
        if not 'template_dir' in config:
            raise ValueError("Option [template_dir] not found in config")
        elif not os.path.isdir(config['template_dir']):
            es = "Specified template folder [%s] does not exist"
            raise ValueError(es % (config['template_dir']))
        __CONFIG = config
        RENDER = web.template.render(__CONFIG['template_dir'], cache=False)
        SERVER_IP = config['server_ip']
    return __CONFIG

def get_server(config_file=None):
    global __SERVER
    if not __SERVER:
        config = get_config(config_file)
        config = get_config()
        if config['zdstack_protocol'].lower() in ('xmlrpc', 'xml-rpc'):
            from xmlrpclib import ServerProxy
            __SERVER = ServerProxy(config['zdstack_address'])
        elif config['zdstack_protocol'].lower() in ('jsonrpc', 'json-rpc'):
            from jsonrpc import ServiceProxy
            __SERVER = ServiceProxy(config['zdstack_address'])
    return __SERVER

def render_main(title=get_config()['title'], heading=get_config()['heading'],
                content='', error=None):
    base_url = get_config()['base_url']
    return RENDER.main(base_url, title, heading, content, error)

