from datetime import datetime, timedelta

from ZDStack import get_configparser
from ZDStack.Server import Server

class ZDStack(Server):

    def __init__(self, name, config_file=None):
        Server.__init__(self, name, get_configparser(config_file))
        self.start_time = datetime.now()
        self.zservs = {}
        for section in self.config.sections():
            if section in zservs:
                es = "Duplicate ZServ configuration section [%s]"
                raise ValueError(es % (section))
            self.zservs[section] = ZServ(section, dict(cp.items(section)), self)

    def start_zserv(self, zserv_name):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        if self.zservs[zserv_name].pid is not None:
            raise Exception("ZServ [%s] is already running" % (zserv_name))
        self.zservs[zserv_name].start()

    def stop_zserv(self, signum=15):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        if self.zservs[zserv_name].pid is None:
            raise Exception("ZServ [%s] is not running" % (zserv_name))
        self.zservs[zserv_name].stop()

    def startup(self):
        Server.startup(self)
        self.start_zserv()

    def shutdown(self):
        self.stop_serving()
        self.stop()
        self.log("Stopping running ZServs")
        for zserv in [z for z in self.zservs.values() if z.pid is not None]:
            zserv.stop()
        self.log("Deleting PID file %s" % (self.pidfile))
        delete_file(self.pidfile)
        sys.exit(0)

