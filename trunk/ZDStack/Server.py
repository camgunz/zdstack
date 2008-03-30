import os
import sys
import time
import signal
import socket
import tempfile
from datetime import datetime
from threading import Thread, Event
from SimpleXMLRPCServer import SimpleXMLRPCServer
from pyfileutils import read_file, append_file, delete_file

from ZDStack import HOSTNAME, SERVICE_ADMIN_SERVER, SERVICE_PASSWORD, \
                    BASE_SERVICE_URL, ZSERV_EXE, send_service_action, \
                    timedelta_in_seconds, rotate_log

class Server(SimpleXMLRPCServer):

    def __init__(self, cp, name):
        self.name = name
        if not name in cp.sections():
            raise ValueError("Could not find %s in server config file" % (name))
        self.config = dict(cp.items(name))
        self.load_config()
        os.chdir(self.workdir)
        self.stats = {}
        self.status = 'Stopped'
        self.keep_serving = Event()

    def load_config(self):
        self.hostname = self.config['hostname']
        if 'rootfolder' in self.config:
            rootfolder = self.config['rootfolder']
        else:
            rootfolder = tempfile.gettempdir()
        if not os.path.isdir(rootfolder):
            raise ValueError("Root folder [%s] does not exist" % (rootfolder))
        self.workdir = os.path.join(rootfolder, self.name)
        if not os.path.isdir(self.workdir):
            os.mkdir(self.workdir)
        self.logfile = os.path.join(self.workdir, self.name + '.log')
        self.pidfile = os.path.join(self.workdir, self.name + '.pid')

    def startup(self):
        self.server = SimpleXMLRPCServer((HOSTNAME, self.port))
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
            self.server.handle_request()

    def handle_signal(self, signum, frame):
        self.log("Received signal [%d]" % (signum))
        if signum == signal.SIGHUP:
            self.load_config()
        else:
            self.shutdown(signum=signum)

    def register_functions(self):
        self.server.register_function(self.get_status)
        self.server.register_function(self.get_logfile)
        self.server.register_function(self.get_stats)
        self.server.register_function(self.start)
        self.server.register_function(self.stop)
        self.server.register_function(self.restart)

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

    def register(self):
        response = send_service_action('register', self.name, self.address)
        return response or True

    def unregister(self):
        response = send_service_action('unregister', self.name, self.address)
        return response or True

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
        self.keep_spawning.set()
        return True

    def stop(self):
        self.log("Stopping")
        self.status = "Stopped"
        self.keep_spawning.clear()
        self.stop_zserv()
        return True

    def restart(self):
        self.log("Restarting")
        self.stop()
        self.start()
        return True

