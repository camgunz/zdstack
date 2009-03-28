import os
import sys
import time
import signal
import socket
import logging
import tempfile
from datetime import datetime
from pyfileutils import read_file, write_file, append_file, delete_file

from ZDStack import RPC_CLASS, get_configfile, set_configfile, \
                    load_configparser, get_configparser, set_debugging
from ZDStack.Utils import resolve_path

class Server:

    """Server represents a daemonized process serving network requests."""

    def __init__(self, debugging=False):
        """Initializes a Server instance.

        debugging:   a boolean, whether or not debugging is enabled

        """
        set_debugging(debugging)
        self.initialize_config()
        ###
        # Normally, daemons chdir to '/', but all the daemonizing logic is
        # contained in the 'zdstack' script.  So there's no reason for us
        # to chdir here, except to be really, really tricky.
        ###
        # os.chdir(self.homedir)
        self.stats = {}
        self.status = 'Stopped'
        self.keep_serving = False
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGQUIT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGHUP, self.handle_signal)

    def initialize_config(self, reload=False):
        """Initializes the server configuration:

        reload:      a boolean, whether or not the configuration is
                     being reloaded

        """
        # logging.debug('')
        self.config_file = get_configfile()
        self.load_config(get_configparser(), reload=reload)

    def load_config(self, config, reload=False):
        """Loads the config.

        reload: a boolean, whether or not the configuration is being
                reloaded

        """
        # logging.debug('')
        defaults = config.defaults()
        hostname = defaults['zdstack_rpc_hostname']
        port = int(defaults['zdstack_port'])
        logfile = os.path.join(defaults['zdstack_log_folder'], 'ZDStack.log')
        pidfile = defaults['zdstack_pid_file']
        self.config = config
        self.defaults = defaults
        self.hostname = hostname
        self.port = port
        self.logfile = logfile
        self.pidfile = pidfile

    def reload_config(self):
        """Reloads the configuration."""
        # logging.debug('')
        self.load_config(get_configparser(reload=True), reload=True)

    def startup(self):
        """Starts the server up."""
        # logging.debug('')
        self.rpc_server = RPC_CLASS((self.hostname, self.port))
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
        ###
        # This could potentially be quite large, maybe we should make this
        # method a little smarter eh?
        ###
        return read_file(self.logfile)

