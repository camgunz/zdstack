import os
import sys
import time
import signal
import socket
import tempfile
from datetime import datetime
from threading import Thread, Event
from DocXMLRPCServer import DocXMLRPCServer
from pyfileutils import read_file, append_file, delete_file

from ZDStack import HOSTNAME, SERVICE_ADMIN_SERVER, SERVICE_PASSWORD, \
                    BASE_SERVICE_URL, ZSERV_EXE, send_service_action, \
                    timedelta_in_seconds, rotate_log

class Server(SimpleXMLRPCServer):

    def __init__(self, cp, fork=True):
        self.config = cp
        self.load_config()
        os.chdir(self.homedir)
        self.stats = {}
        self.status = 'Stopped'
        self.keep_serving = Event()
        # signal.signal(signal.SIGINT, self.handle_signal)
        # signal.signal(signal.SIGQUIT, self.handle_signal)
        # signal.signal(signal.SIGTERM, self.handle_signal)
        # signal.signal(signal.SIGHUP, self.handle_signal)
        # self.register()
        # self.should_fork = fork

    def _fork(self):
        if hasattr(os, 'devnull'):
            stdin = os.devnull
        else:
            stdin = '/dev/null'
        stdout = stderr = self.logfile
        if os.fork():
            os._exit(0)
        os.chdir('/')
        os.umask(0)
        os.setsid()
        if os.fork():
            os._exit(0)
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(stdin, 'r')
        so = open(self.logfile, 'a+')
        se = open(self.logfile, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        pid = str(os.getpid())
        write_file(pid, self.pidfile)

    def load_config(self):
        if 'rootfolder' in self.config:
            self.rootfolder = self.config['rootfolder']
        else:
            self.rootfolder = tempfile.gettempdir()
        if not os.path.isdir(rootfolder):
            raise ValueError("Root folder [%s] does not exist" % (rootfolder))
        self.homedir = os.path.join(rootfolder, self.name)
        if not os.path.isdir(self.homedir):
            os.mkdir(self.homedir)
        self.logfile = os.path.join(self.homedir, self.name + '.log')
        self.pidfile = os.path.join(self.homedir, self.name + '.pid')
        self.configfile = os.path.join(self.homedir, self.name + '.cfg')

    def startup(self):
        if self.should_fork:
            self._fork()
        self.xmlrpc_server = DocXMLRPCServer((HOSTNAME, self.port))
        self.register_functions()
        self.serving_thread = Thread(target=self._serve)
        self.serving_thread.setDaemon(True)
        self.serving_thread.start()
        self.start()
        self.start_serving()

    def shutdown(self, signum=15):
        self.stop_serving()
        self.stop()
        sys.exit(0)

    def _serve(self):
        while 1:
            self.keep_serving.wait()
            self.xmlrpc_server.handle_request()

    def handle_signal(self, signum, frame):
        self.log("Received signal [%d]" % (signum))
        if signum == signal.SIGHUP:
            self.load_config()
        else:
            self.shutdown(signum=signum)

    def register_functions(self):
        self.xmlrpc_server.register_function(self.get_status)
        self.xmlrpc_server.register_function(self.get_logfile)
        self.xmlrpc_server.register_function(self.get_stats)
        self.xmlrpc_server.register_function(self.start)
        self.xmlrpc_server.register_function(self.stop)
        self.xmlrpc_server.register_function(self.restart)

    def start_serving(self):
        self.keep_serving.set()

    def stop_serving(self):
        self.keep_serving.clear()

    def log(self, s):
        log_msg = "[%s] %s\n" % (time.ctime(), s)
        append_file(log_msg, self.logfile)

    def debug(self, s):
        if DEBUG:
            debug_msg = "DEBUG: %s" % (s)
            self.log(debug_msg)

    def get_status(self):
        return self.status

    def get_logfile(self):
        return read_file(self.logfile)

    def get_stats(self):
        s = {}
        for x, y in self.stats.items():
            s[x] = y
        s['Runtime'] = timedelta_in_seconds(datetime.now() - self.start_time)
        return s

    def start(self):
        self.log("Starting")
        self.status = "Running"
        return True

    def stop(self):
        self.log("Stopping")
        self.status = "Stopped"
        return True

    def restart(self):
        self.log("Restarting")
        self.stop()
        self.start()
        return True

