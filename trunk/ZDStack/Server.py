import os
import sys
import time
import signal
import socket
import logging
import tempfile
from datetime import datetime
from pyfileutils import read_file, write_file, append_file, delete_file

from ZDStack import HOSTNAME, get_configfile, set_configfile, \
                    load_configparser, get_configparser, set_debugging, log
from ZDStack.XMLRPCServer import XMLRPCServer
from ZDStack.SimpleJSONRPCServer import SimpleJSONRPCServer

class Server:

    """Server represents a daemonized process serving network requests."""

    def __init__(self, config_file=None, debugging=False):
        """Initializes a Server instance.

        config_file: a string representing the full path to a
                     configuration file
        debugging:   a boolean, whether or not debugging is enabled

        """
        set_debugging(debugging)
        self.initialize_config(config_file)
        os.chdir(self.homedir)
        self.stats = {}
        self.status = 'Stopped'
        self.keep_serving = False
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGQUIT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGHUP, self.handle_signal)

    def initialize_config(self, config_file=None, reload=False):
        """Initializes the server configuration:

        config_file: a string representing the full path to a
                     configuration file
        reload:      a boolean, whether or not the configuration is
                     being reloaded

        """
        logging.getLogger('').debug('')
        if not config_file:
            self.config_file = get_configfile()
        else:
            self.config_file = config_file
            set_configfile(config_file)
        self.config = get_configparser()
        self.load_config(reload=reload)

    def load_config(self, reload=False):
        """Loads the config.

        reload: a boolean, whether or not the configuration is being
                reloaded

        """
        logging.getLogger('').debug('')
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
        if not 'rpc_protocol' in self.defaults:
            es = "Could not find option 'rpc_protocol' in the configuration"
            raise ValueError(es)
        if self.defaults['rpc_protocol'].lower() in ('jsonrpc', 'json-rpc'):
            self.rpc_class = SimpleJSONRPCServer
        elif self.defaults['rpc_protocol'].lower() in ('xmlrpc', 'xml-rpc'):
            self.rpc_class = XMLRPCServer
        else:
            es = "RPC Protocol [%s] not supported"
            raise ValueError(es % (self.defaults['rpc_protocol']))
        if 'rpc_hostname' in self.defaults:
            self.hostname = self.defaults['xmlrpc_hostname']
        else:
            self.hostname = HOSTNAME
        self.port = int(self.defaults['zdstack_port'])
        self.homedir = rootfolder
        self.logfile = os.path.join(self.homedir, 'ZDStack.log')
        self.pidfile = os.path.join(self.homedir, 'ZDStack.pid')

    def reload_config(self):
        """Reloads the configuration."""
        logging.getLogger('').debug('')
        self.config = get_configparser(reload=True)
        self.load_config(reload=True)

    def startup(self):
        """Starts the server up."""
        logging.getLogger('').debug('')
        self.rpc_server = self.rpc_class((HOSTNAME, self.port))
        self.register_functions()
        self.keep_serving = True
        self.status = "Running"
        write_file(str(os.getpid()), self.pidfile)
        self.start()
        while self.keep_serving:
            self.rpc_server.handle_request()

    def shutdown(self, signum=15):
        """Shuts the server down."""
        logging.getLogger('').debug('')
        self.stop()
        self.keep_serving = False
        try:
            delete_file(self.pidfile)
        except OSError, e:
            log("Error removing PID file %s: [%s]" % (self.pidfile, e))
        sys.exit(0)

    def start(self):
        """Starts serving requests."""
        logging.getLogger('').debug('')
        raise NotImplementedError()

    def stop(self):
        """Stops serving requests."""
        logging.getLogger('').debug('')
        raise NotImplementedError()

    def restart(self):
        """Restarts the server."""
        logging.getLogger('').debug('')
        self.stop()
        self.start()
        return True

    def handle_signal(self, signum, frame):
        """Handles a signal."""
        logging.getLogger('').debug('')
        if signum == signal.SIGHUP:
            self.reload_config()
        else:
            self.shutdown(signum=signum)

    def register_functions(self):
        """Registers public XML-RPC functions."""
        logging.getLogger('').debug('')
        self.rpc_server.register_function(self.get_status)
        self.rpc_server.register_function(self.get_logfile)
        self.rpc_server.register_function(self.reload_config)
        self.rpc_server.register_function(self.start)
        self.rpc_server.register_function(self.stop)
        self.rpc_server.register_function(self.restart)

    def get_status(self):
        """Returns the current status of the server."""
        logging.getLogger('').debug('')
        return self.status

    def get_logfile(self):
        """Returns the contents of this server's logfile."""
        logging.getLogger('').debug('')
        return read_file(logfile)

