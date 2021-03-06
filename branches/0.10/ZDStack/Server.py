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
                    load_configparser, get_configparser, set_debugging

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
        # logging.debug('')
        if config_file:
            set_configfile(config_file)
        self.config_file = get_configfile()
        self.load_config(get_configparser(), reload=reload)

    def load_config(self, config, reload=False):
        """Loads the config.

        reload: a boolean, whether or not the configuration is being
                reloaded

        """
        # logging.debug('')
        ###
        # TODO:
        #   Split this up in to check_config and load_config methods.
        ###
        defaults = config.defaults()
        if 'rootfolder' in defaults:
            rootfolder = defaults['rootfolder']
        else:
            rootfolder = tempfile.gettempdir()
        if not os.path.isdir(rootfolder):
            raise ValueError("Root folder [%s] does not exist" % (rootfolder))
        if not 'zdstack_port' in defaults:
            es = "Could not find option 'zdstack_port' in the configuration"
            raise ValueError(es)
        if not 'rpc_protocol' in defaults:
            es = "Could not find option 'rpc_protocol' in the configuration"
            raise ValueError(es)
        if defaults['rpc_protocol'].lower() in ('jsonrpc', 'json-rpc'):
            from ZDStack.SimpleJSONRPCServer import SimpleJSONRPCServer
            rpc_class = SimpleJSONRPCServer
        elif defaults['rpc_protocol'].lower() in ('xmlrpc', 'xml-rpc'):
            from ZDStack.XMLRPCServer import XMLRPCServer
            rpc_class = XMLRPCServer
        else:
            es = "RPC Protocol [%s] not supported"
            raise ValueError(es % (defaults['rpc_protocol']))
        if 'rpc_hostname' in defaults:
            hostname = defaults['xmlrpc_hostname']
        else:
            hostname = HOSTNAME
        port = int(defaults['zdstack_port'])
        homedir = rootfolder
        logfile = os.path.join(homedir, 'ZDStack.log')
        pidfile = os.path.join(homedir, 'ZDStack.pid')
        self.config = config
        self.defaults = defaults
        self.rpc_class = rpc_class
        self.hostname = hostname
        self.port = port
        self.homedir = homedir
        self.logfile = logfile
        self.pidfile = pidfile

    def reload_config(self):
        """Reloads the configuration."""
        # logging.debug('')
        self.load_config(get_configparser(reload=True), reload=True)

    def startup(self):
        """Starts the server up."""
        # logging.debug('')
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
        # logging.debug('')
        self.stop()
        self.keep_serving = False
        try:
            delete_file(self.pidfile)
        except OSError, e:
            logging.info("Error removing PID file %s: [%s]" % (self.pidfile, e))
        sys.exit(0)

    def start(self):
        """Starts serving requests."""
        # logging.debug('')
        raise NotImplementedError()

    def stop(self):
        """Stops serving requests."""
        # logging.debug('')
        raise NotImplementedError()

    def restart(self):
        """Restarts the server."""
        # logging.debug('')
        self.stop()
        self.start()
        return True

    def handle_signal(self, signum, frame):
        """Handles a signal."""
        # logging.debug('')
        if signum == signal.SIGHUP:
            self.reload_config()
        else:
            self.shutdown(signum=signum)

    def register_functions(self):
        """Registers public XML-RPC functions."""
        # logging.debug('')
        self.rpc_server.register_function(self.get_status)
        self.rpc_server.register_function(self.get_logfile)
        self.rpc_server.register_function(self.reload_config)
        self.rpc_server.register_function(self.start)
        self.rpc_server.register_function(self.stop)
        self.rpc_server.register_function(self.restart)

    def get_status(self):
        """Returns the current status of the server."""
        # logging.debug('')
        return self.status

    def get_logfile(self):
        """Returns the contents of this server's logfile."""
        # logging.debug('')
        return read_file(logfile)

