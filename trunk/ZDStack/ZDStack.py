from datetime import datetime, timedelta

from ZDStack import get_configparser
from ZDStack.ZServ import ZServ
from ZDStack.Server import Server

class AuthenticationError(Exception):

    def __init__(self, username, method):
        es = "Error: Access to method [%s] was denied for user [%s]"
        Exception.__init__(self, es % (method, username))

class ZDStack(Server):

    methods_requiring_authentication = []

    def __init__(self, name, config_file=None):
        Server.__init__(self, name, get_configparser(config_file))
        self.start_time = datetime.now()
        self.zservs = {}
        for section in self.config.sections():
            if section in zservs:
                es = "Duplicate ZServ configuration section [%s]"
                raise ValueError(es % (section))
            self.zservs[section] = ZServ(section, dict(cp.items(section)), self)
        try:
            self.username = self.config.defaults()['username']
            self.password = self.config.defaults()['password']
        except KeyError, e:
            es = "Could not find option %s in configuration file"
            raise ValueError(es % (str(e)))
        self.methods_requiring_authentication.append('start_zserv')
        self.methods_requiring_authentication.append('stop_zserv')
        self.methods_requiring_authentication.append('start_all_zservs')
        self.methods_requiring_authentication.append('stop_all_zservs')

    def _dispatch(self, method, params):
        if method in self.methods_requiring_authentication:
            if not self.authenticate(params[0], params[1]):
                raise AuthenticationError(params[0], method)
        try:
            func = getattr(self, method)
            if not type(func) == type(get_configparser):
                raise AttributeError
        except AttributeError:
            raise Exception('method "%s" is not supported' % (method))
        else:
            return func(*params)

    def authenticate(self, username, password):
        return username == self.username and password == self.password

    def start_zserv(self, zserv_name):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        if self.zservs[zserv_name].pid is not None:
            raise Exception("ZServ [%s] is already running" % (zserv_name))
        self.zservs[zserv_name].start()

    def stop_zserv(self):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        if self.zservs[zserv_name].pid is None:
            raise Exception("ZServ [%s] is not running" % (zserv_name))
        self.zservs[zserv_name].stop()

    def start_all_zservs(self):
        for zserv in self.zservs.values():
            zserv.start()

    def stop_all_zservs(self):
        for zserv in [z for z in self.zservs.values() if z.pid is not None]:
            zserv.stop()

    def start(self):
        Server.start(self)
        self.start_all_zservs()
        return True

    def stop(self):
        Server.stop(self)
        self.stop_all_zservs()
        return True

    def shutdown(self):
        self.stop_serving()
        self.stop()
        self.log("Deleting PID file %s" % (self.pidfile))
        delete_file(self.pidfile)
        sys.exit(0)

    def register_functions(self):
        for x in (self.start_zserv, self.stop_zserv, self.start_all_zservs,
                  self.stop_all_zservs):
            self.register_function(x)

