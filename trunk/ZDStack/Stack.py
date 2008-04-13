import os.path

from datetime import datetime, timedelta
from threading import Thread

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
        Server.__init__(self, get_configparser(config_file))
        self.start_time = datetime.now()
        self.zservs = {}
        for section in self.config.sections():
            if section in self.zservs:
                es = "Duplicate ZServ configuration section [%s]"
                raise ValueError(es % (section))
            zs_config = dict(self.config.items(section))
            if not 'type' in zs_config:
                es = "Could not determine type of server [%s]"
                raise ValueError(es % (section))
            if zs_config['type'].lower() == 'ctf':
                zs = CTF(section, zs_config, self)
            elif zs_config['type'].lower() == 'coop':
                zs = Coop(section, zs_config, self)
            elif zs_config['type'].lower() in ('duel', '1-on-1'):
                zs = Duel(section, zs_config, self)
            elif zs_config['type'].lower() == 'ffa':
                zs = FFA(section, zs_config, self)
            elif zs_config['type'].lower() == 'teamdm':
                zs = TeamDM(section, zs_config, self)
            else:
                es = "Invalid server type [%s]"
                raise ValueError(es % (zs_config['type']))
            self.zservs[section] = zs
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
        Thread(target=self.zservs[zserv_name].start).start()

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

    def get_zserv(self, zserv_name):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        zserv = self.zservs[zserv_name]
        return Dictable({'name': zserv.name,
                         'type': zserv.type,
                         'port': zserv.port,
                         'iwad': zserv.base_iwad,
                         'wads': [os.path.basename(x) for x in zserv.wads],
                         'optional_wads': zserv.optional_wads,
                         'maps': zserv.maps,
                         'dmflags': zserv.dmflags,
                         'dmflags2': zserv.dmflags2,
                         'admin_email': zserv.admin_email,
                         'website': zserv.website.replace('\\', '/'),
                         'advertise': zserv.advertise,
                         'hostname': zserv.hostname,
                         'motd': zserv.motd.replace('<br>', '\n'),
                         'remove_bots_when_humans':
                                                zserv.remove_bots_when_humans,
                         'overtime': zserv.overtime,
                         'skill': zserv.skill,
                         'gravity': zserv.gravity,
                         'air_control': zserv.air_control,
                         'min_players': zserv.min_players,
                         'max_players': zserv.max_players,
                         'max_clients': zserv.max_clients,
                         'max_teams': zserv.max_teams,
                         'max_players_per_team': zserv.max_players_per_team,
                         'teamdamage': zserv.teamdamage,
                         'deathlimit': zserv.deathlimit,
                         'timelimit': zserv.timelimit,
                         'fraglimit': zserv.fraglimit,
                         'scorelimit': zserv.scorelimit,
                         'spam_window': zserv.spam_window,
                         'spam_limit': zserv.spam_limit,
                         'speed_check': zserv.speed_check,
                         'restart_empty_map': zserv.restart_empty_map,
                         'map_number': zserv.map.number,
                         'map_name': zserv.map.name}).export()

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
        return self.zservs[zserv_name].players.export()

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
        return self.zservs[zserv_name].map.export()

    def get_remembered_stats(self, zserv_name):
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        return self.zservs[zserv_name].remembered_stats.export()

    def register_functions(self):
        for x in (self.start_zserv, self.stop_zserv, self.restart_zserv,
                  self.start_all_zservs, self.stop_all_zservs,
                  self.restart_all_zservs, self.get_zserv, self.get_all_zservs,
                  self.list_zserv_names, self.get_remembered_stats,
                  self.get_current_map, self.get_team, self.get_all_teams,
                  self.get_player, self.get_all_players,
                  self.list_player_names):
            self.xmlrpc_server.register_function(x)

