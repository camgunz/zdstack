import sys
import os.path

from datetime import datetime, timedelta

from pyfileutils import delete_file

from ZDStack import get_configparser
from ZDStack.CTF import CTF
from ZDStack.Coop import Coop
from ZDStack.Duel import Duel
from ZDStack.FFA import FFA
from ZDStack.TeamDM import TeamDM
from ZDStack.Server import Server
from ZDStack.Dictable import Dictable
from ZDStack.Listable import Listable

class AuthenticationError(Exception):

    def __init__(self, username, method):
        es = "Error: Access to method [%s] was denied for user [%s]"
        Exception.__init__(self, es % (method, username))

class Stack(Server):

    methods_requiring_authentication = []

    def __init__(self, config_file=None):
        self.config_file = config_file
        self.zservs = {}
        self.start_time = datetime.now()
        Server.__init__(self, get_configparser(config_file))
        self.methods_requiring_authentication.append('start_zserv')
        self.methods_requiring_authentication.append('stop_zserv')
        self.methods_requiring_authentication.append('start_all_zservs')
        self.methods_requiring_authentication.append('stop_all_zservs')

    def check_all_zserv_configs(self):
        for section in self.config.sections():
            self.check_zserv_config(dict(self.config.items(section)))

    def check_zserv_config(self, zserv_config):
        if not 'type' in zserv_config:
            es = "Could not determine type of server [%s]"
            raise ValueError(es % (section))
        if zserv_config['type'].lower() not in \
                        ('ctf', 'coop', 'duel', '1-on-1', 'ffa', 'teamdm'):
            es = "Invalid server type [%s]"
            raise ValueError(es % (zserv_config['type']))

    def load_zservs(self):
        self.log("Stack: load_zservs")
        for zserv_name in self.config.sections():
            zs_config = dict(self.config.items(zserv_name))
            if zserv_name in self.zservs:
                self.log("Stack: Reloading Config for [%s]" % (zserv_name))
                self.zservs[zserv_name].reload_config(zs_config)
            elif zs_config['type'].lower() == 'ctf':
                self.log("Stack: Adding zserv [%s]" % (zserv_name))
                self.zservs[zserv_name] = CTF(zserv_name, zs_config, self)
            elif zs_config['type'].lower() == 'coop':
                self.log("Stack: Adding zserv [%s]" % (zserv_name))
                self.zservs[zserv_name] = Coop(zserv_name, zs_config, self)
            elif zs_config['type'].lower() in ('duel', '1-on-1'):
                self.log("Stack: Adding zserv [%s]" % (zserv_name))
                self.zservs[zserv_name] = Duel(zserv_name, zs_config, self)
            elif zs_config['type'].lower() == 'ffa':
                self.log("Stack: Adding zserv [%s]" % (zserv_name))
                self.zservs[zserv_name] = FFA(zserv_name, zs_config, self)
            elif zs_config['type'].lower() == 'teamdm':
                self.log("Stack: Adding zserv [%s]" % (zserv_name))
                self.zservs[zserv_name] = TeamDM(zserv_name, zs_config, self)

    def load_config(self, reload=False):
        self.config = get_configparser(self.config_file)
        Server.load_config(self, reload)
        self.check_all_zserv_configs()
        self.load_zservs()
        try:
            self.username = self.config.defaults()['username']
            self.password = self.config.defaults()['password']
        except KeyError, e:
            es = "Could not find option %s in configuration file"
            raise ValueError(es % (str(e)))

    def _dispatch(self, method, params):
        if method in self.methods_requiring_authentication:
            if not self.authenticate(params[0], params[1]):
                raise AuthenticationError(params[0], method)
            s = "Authentication user [%s] for method [%s]"
            self.log(s % (params[0], method))
        else:
            self.log("Method [%s] did not require authentication" % (method))
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

    def stop_zserv(self, zserv_name):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        if self.zservs[zserv_name].pid is None:
            raise Exception("ZServ [%s] is not running" % (zserv_name))
        self.zservs[zserv_name].stop()

    def restart_zserv(self, zserv_name):
        self.stop_zserv(zserv_name)
        time.sleep(1)
        self.start_zserv(zserv_name)

    def start_all_zservs(self):
        for zserv_name in self.zservs:
            self.start_zserv(zserv_name)

    def stop_all_zservs(self):
        for zserv in [z for z in self.zservs.values() if z.pid is not None]:
            zserv.stop()

    def restart_all_zservs(self):
        for zserv in [z for z in self.zservs.values() if z.pid is not None]:
            zserv.restart()

    def start(self):
        self.start_all_zservs()
        return True

    def stop(self):
        self.stop_all_zservs()
        return True

    def get_zserv(self, zserv_name):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        return self.zservs[zserv_name].export()

    def get_all_zservs(self):
        return [self.get_zserv(x) for x in self.zservs]

    def list_zserv_names(self):
        return self.zservs.keys()

    def get_player(self, zserv_name, player_name):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        elif player_name not in self.zservs[zserv_name].players:
            raise ValueError("Player [%s] not found" % (player_name))
        return self.zservs[zserv_name].players[player_name]

    def get_all_players(self, zserv_name):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        players = self.zservs[zserv_name].players
        return players.export()

    def list_player_names(self, zserv_name):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        return self.zservs[zserv_name].players.keys()

    def get_team(self, zserv_name, team_color):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        elif team_color not in self.zservs[zserv_name].teams:
            raise ValueError("Team [%s] not found" % (team_color))
        return self.zservs[zserv_name].teams[team_color]

    def get_all_teams(self, zserv_name):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        return self.zservs[zserv_name].teams.export()

    def get_current_map(self, zserv_name):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        if self.zservs[zserv_name].map:
            return self.zservs[zserv_name].map.export()
        else:
            return None

    def get_remembered_stats(self, zserv_name):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        return self.zservs[zserv_name].remembered_stats.export()

    def send_to_zserv(self, zserv_name, message):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        return self.zservs[zserv_name].send_to_zserv(message)

    def register_functions(self):
        Server.register_functions(self)
        for x in (self.start_zserv, self.stop_zserv, self.restart_zserv,
                  self.start_all_zservs, self.stop_all_zservs,
                  self.restart_all_zservs, self.get_zserv, self.get_all_zservs,
                  self.list_zserv_names, self.get_remembered_stats,
                  self.get_current_map, self.get_team, self.get_all_teams,
                  self.get_player, self.get_all_players,
                  self.list_player_names, self.send_to_zserv):
            self.xmlrpc_server.register_function(x)

