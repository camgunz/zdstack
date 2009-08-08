import os
import sys
import time
import signal
import socket
import tempfile
from datetime import datetime

from ZDStack import ZDSThreadPool
from ZDStack import DIE_THREADS_DIE, get_configfile, set_configfile, \
                    load_configparser, get_configparser, set_debugging, \
                    get_rpc_server_class, get_zdslog
from ZDStack.Utils import resolve_path

zdslog = get_zdslog()

class Server(object):

    """Server represents a daemonized process serving network requests.

    .. attribute:: stats
        A dict of server stats.

    .. attribute:: status
        A string representing the server's status.

    .. attribute:: hostname
        A string representing the server's hostname.

    .. attribute:: port
        An int representing the server's port.

    .. attribute:: logfile
        A string representing the server's logfile

    .. attribute:: pidfile
        A string representing the server's PID file

    .. attribute:: username
        A string representing the authenticating username

    .. attribute:: password
        A string representing the authenticating password

    """

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

        :param reload: whether or not the config is being reloaded
        :type reload: boolean

        """
        # zdslog.debug('')
        self.config_file = get_configfile()
        self.load_config(get_configparser(reload=reload), reload=reload)

    def load_config(self, config, reload=False):
        """Loads the config.

        :param config: the config to load
        :type config: :class:`~ZDStack.ZDSConfigParser.ZDSConfigParser`
        :param reload: whether or not the config is being reloaded
        :type reload: boolean

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
        if os.path.isfile(self.pidfile):
            es = "PID file [%s] already exists, is ZDStack already running?"
            raise Exception(es % (self.pidfile))

        if os.fork():
            os._exit(0)
        os.chdir('/')
        os.umask(0)
        os.setsid()
        if os.fork():
            os._exit(0)

        # print "Closing STDIN, STDOUT & STDERR"
        # for x in [sys.stdin, sys.stdout, sys.stderr]:
        #     try:
        #         os.close(x.fileno())
        #     except Exception, e:
        #         zdslog.debug("Exception closing %s: %s" % (x, e))
        #         continue
        ###
        # print "Closing STDIN, STDOUT & STDERR again"
        os.close(sys.stdin.fileno())
        sys.stdin.close()
        sys.stdout.flush()
        os.close(sys.stdout.fileno())
        sys.stdout.close()
        sys.stderr.flush()
        os.close(sys.stderr.fileno())
        sys.stderr.close()
        ###
        sys.stdin = open('/dev/null', 'r+b')
        sys.stdout = open(self.logfile, 'a+b')
        sys.stderr = open(self.logfile, 'a+b')
        print "STDOUT now redirected to %s" % (self.logfile)
        print >> sys.stderr, "STDERR now redirected to %s" % (self.logfile)

        pid_fobj = open(self.pidfile, 'w')
        pid_fobj.write(str(os.getpid()))
        pid_fobj.flush()
        pid_fobj.close()

        self.start()
        zdslog.info("ZDStack listening on %s:%s" % addr)
        zdslog.info("ZDStack Startup Complete")
        while self.keep_serving:
            self.rpc_server.handle_request()

    def shutdown(self, signum=15, retval=0):
        """Shuts the server down.
        
        :param signum: unused
        :param retval: the exit code to use if exit was successful
        :type retval: integer
        
        """
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
            os.unlink(self.pidfile)
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

    def get_status(self):
        """Gets the current status of the server.
        
        :returns: ZDStack's current status as a server
        :rtype: string
        
        """
        # zdslog.debug('')
        return self.status

    def get_logfile(self):
        """Gets the contents of this server's logfile.
        
        :returns: the contents of ZDStack's logfile.
        :rtype: string

        This logfile can be really large if debugging is enabled, fair
        warning.
        
        """
        # zdslog.debug('')
        ###
        # This could potentially be quite large, maybe we should make this
        # method a little smarter eh?
        ###
        fobj = open(self.logfile)
        data = fobj.read()
        fobj.close()
        return data

