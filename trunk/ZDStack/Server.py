import os
import sys
import time
import signal
import socket
import tempfile
from datetime import datetime
from pyfileutils import read_file, write_file, append_file, delete_file

from ZDStack import ZDSThreadPool
from ZDStack import DIE_THREADS_DIE, get_configfile, set_configfile, \
                    load_configparser, get_configparser, set_debugging, \
                    get_rpc_server_class, get_zdslog
from ZDStack.Utils import resolve_path

zdslog = get_zdslog()

class Server(object):

    """Server represents a daemonized process serving network requests."""

    def __init__(self):
        """Initializes a Server instance."""
        self.initialize_config()
        ###
        # Normally, daemons chdir to '/', but all the daemonizing logic is
        # contained in the 'zdstack' script.  So there's no reason for us
        # to chdir here, except to be really, really tricky.
        ###
        # os.chdir(self.home_folder)
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
        # zdslog.debug('')
        self.config_file = get_configfile()
        self.load_config(get_configparser(reload=reload), reload=reload)

    def load_config(self, config, reload=False):
        """Loads the config.

        reload: a boolean, whether or not the configuration is being
                reloaded

        """
        zdslog.debug('')
        hostname = config.get('DEFAULT', 'zdstack_rpc_hostname')
        port = config.getint('DEFAULT', 'zdstack_port')
        log_folder = config.getpath('DEFAULT', 'zdstack_log_folder')
        logfile = os.path.join(log_folder, 'ZDStack.log')
        pidfile = config.getpath('DEFAULT', 'zdstack_pid_file')
        username = config.get('DEFAULT', 'zdstack_username')
        password = config.get('DEFAULT', 'zdstack_password')
        self.config = config
        self.hostname = hostname
        self.port = port
        self.logfile = logfile
        self.pidfile = pidfile
        self.username = username
        self.password = password

    def reload_config(self):
        """Reloads the configuration."""
        # zdslog.debug('')
        self.load_config(get_configparser(reload=True), reload=True)

    def startup(self):
        """Starts the server up."""
        # zdslog.debug('')
        zdslog.info("ZDStack Starting Up")
        addr = (self.hostname, self.port)
        RPCServer = get_rpc_server_class()
        self.rpc_server = RPCServer(addr, self.username, self.password)
        self.rpc_server.timeout = 1
        self.register_functions()
        self.keep_serving = True
        write_file(str(os.getpid()), self.pidfile)
        self.start()
        zdslog.info("ZDStack listening on %s:%s" % addr)
        zdslog.info("ZDStack Startup Complete")
        while self.keep_serving:
            self.rpc_server.handle_request()

    def shutdown(self, signum=15, retval=0):
        """Shuts the server down."""
        # zdslog.debug('')
        zdslog.info("ZDStack Shutting Down")
        self.stop()
        zdslog.debug("Setting keep_serving False")
        self.keep_serving = False
        zdslog.debug("Setting DIE_THREADS_DIE True")
        DIE_THREADS_DIE = True
        zdslog.debug("Joining all threads")
        ZDSThreadPool.join_all()
        try:
            zdslog.debug("Deleting PID file")
            delete_file(self.pidfile)
        except OSError, e:
            if e.errno != 2:
                ###
                # Error code 2: No such file or directory
                ###
                es = "Error removing PID file %s: [%s]"
                zdslog.error(es % (self.pidfile, e))
        zdslog.info("ZDStack Shutdown Complete")
        sys.exit(retval)

    def start(self):
        """Starts serving requests."""
        # zdslog.debug('')
        self.status = "Running"

    def stop(self):
        """Stops serving requests."""
        # zdslog.debug('')
        self.status = "Stopped"

    def restart(self):
        """Restarts the server."""
        # zdslog.debug('')
        self.stop()
        self.start()

    def handle_signal(self, signum, frame):
        """Handles a signal."""
        # zdslog.debug('')
        if signum == signal.SIGHUP:
            self.reload_config()
        else:
            self.shutdown(signum=signum)

    def register_functions(self):
        """Registers public XML-RPC functions."""
        # zdslog.debug('')
        self.rpc_server.register_function(self.get_status)
        self.rpc_server.register_function(self.get_logfile,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.reload_config,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.start,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.stop,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.restart,
                                          requires_authentication=True)

    def get_status(self):
        """Returns the current status of the server."""
        # zdslog.debug('')
        return self.status

    def get_logfile(self):
        """Returns the contents of this server's logfile."""
        # zdslog.debug('')
        ###
        # This could potentially be quite large, maybe we should make this
        # method a little smarter eh?
        ###
        return read_file(self.logfile)

