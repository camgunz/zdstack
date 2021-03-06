import os
import sys
import time
import signal
import socket
import tempfile
from datetime import datetime
from pyfileutils import read_file, write_file, append_file, delete_file

from ZDStack import HOSTNAME, get_configparser, set_debugging, log, debug
from ZDStack.XMLRPCServer import XMLRPCServer

class Server:

    def __init__(self, config_parser, debugging=False):
        set_debugging(debugging)
        self.config = config_parser
        self.config_file = config_parser.filename
        self.load_config()
        os.chdir(self.homedir)
        self.stats = {}
        self.status = 'Stopped'
        self.keep_serving = False
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGQUIT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGHUP, self.handle_signal)

    def load_config(self, reload=False):
        debug()
        self.defaults = self.config.defaults()
        if 'rootfolder' in self.defaults:
            rootfolder = self.defaults['rootfolder']
        else:
            rootfolder = tempfile.gettempdir()
        if not os.path.isdir(rootfolder):
            raise ValueError("Root folder [%s] does not exist" % (rootfolder))
        if not 'zdstack_port' in self.defaults:
            es = "Could not find option 'zdstack_port' in the configuration"
            raise ValueError(es)
        if 'xmlrpc_hostname' in self.defaults:
            self.hostname = self.defaults['xmlrpc_hostname']
        else:
            self.hostname = HOSTNAME
        self.port = int(self.defaults['zdstack_port'])
        self.homedir = rootfolder
        self.logfile = os.path.join(self.homedir, 'ZDStack.log')
        self.pidfile = os.path.join(self.homedir, 'ZDStack.pid')

    def reload_config(self):
        debug()
        self.config = get_configparser(reload=True,
                                       config_file=self.config_file)
        self.load_config(reload=True)

    def startup(self):
        debug()
        self.xmlrpc_server = XMLRPCServer((HOSTNAME, self.port))
        self.register_functions()
        self.keep_serving = True
        self.status = "Running"
        write_file(str(os.getpid()), self.pidfile)
        self.start()
        while self.keep_serving:
            self.xmlrpc_server.handle_request()

    def shutdown(self, signum=15):
        debug()
        self.stop()
        self.keep_serving = False
        try:
            delete_file(self.pidfile)
        except OSError, e:
            log("Error removing PID file %s: [%s]" % (self.pidfile, e))
        sys.exit(0)

    def start(self):
        debug()
        raise NotImplementedError()

    def stop(self):
        debug()
        raise NotImplementedError()

    def restart(self):
        debug()
        self.stop()
        self.start()
        return True

    def handle_signal(self, signum, frame):
        debug()
        if signum == signal.SIGHUP:
            self.reload_config()
        else:
            self.shutdown(signum=signum)

    def register_functions(self):
        debug()
        self.xmlrpc_server.register_function(self.get_status)
        self.xmlrpc_server.register_function(self.get_logfile)
        self.xmlrpc_server.register_function(self.reload_config)
        self.xmlrpc_server.register_function(self.start)
        self.xmlrpc_server.register_function(self.stop)
        self.xmlrpc_server.register_function(self.restart)

    def get_status(self):
        debug()
        return self.status

    def get_logfile(self):
        debug()
        return read_file(logfile)

