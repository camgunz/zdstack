import time
import logging

from datetime import datetime
from threading import Lock
from cStringIO import StringIO

from ZDStack import get_configparser, log
from ZDStack.Utils import yes
from ZDStack.Server import Server
from ZDStack.ZServDepot import get_zserv_class
from ZDStack.ZDSConfigParser import RawZDSConfigParser as RCP

class AuthenticationError(Exception):

    def __init__(self, username, method):
        es = "Error: Access to method [%s] was denied for user [%s]"
        Exception.__init__(self, es % (method, username))

class Stack(Server):

    methods_requiring_authentication = []

    def __init__(self, config_file=None, debugging=False):
        self.config_file = config_file
        self.spawn_lock = Lock()
        self.zservs = {}
        self.start_time = datetime.now()
        Server.__init__(self, get_configparser(config_file), debugging)
        self.methods_requiring_authentication.append('start_zserv')
        self.methods_requiring_authentication.append('stop_zserv')
        self.methods_requiring_authentication.append('start_all_zservs')
        self.methods_requiring_authentication.append('stop_all_zservs')

    def check_all_zserv_configs(self):
        logging.getLogger('').debug('')
        for section in self.config.sections():
            self.check_zserv_config(dict(self.config.items(section)))

    def check_zserv_config(self, zserv_config):
        logging.getLogger('').debug('')
        if not 'type' in zserv_config:
            es = "Could not determine type of server [%s]"
            raise ValueError(es % (section))
        if zserv_config['type'].lower() not in \
                                    ('ctf', 'coop', 'duel', 'ffa', 'teamdm'):
            es = "Invalid server type [%s]"
            raise ValueError(es % (zserv_config['type']))

    def load_zservs(self):
        logging.getLogger('').debug('')
        for zserv_name in self.config.sections():
            zs_config = dict(self.config.items(zserv_name))
            if zserv_name in self.zservs:
                log("Reloading Config for [%s]" % (zserv_name))
                self.zservs[zserv_name].reload_config(zs_config)
            else:
                game_mode = zs_config['type'].lower()
                memory_slots = int(zs_config['maps_to_remember'])
                log_ips = yes(zs_config['enable_ip_logging'])
                load_plugins = yes(zs_config['load_plugins'])
                zs_class = get_zserv_class(game_mode, memory_slots,
                                           log_ips, load_plugins)
                zs = zs_class(zserv_name, zs_config, self)
                # log("Adding zserv [%s]" % (zserv_name))
                self.zservs[zserv_name] = zs

    def load_config(self, reload=False):
        logging.getLogger('').debug('')
        self.config = get_configparser(self.config_file)
        self.raw_config = RCP(self.config_file, allow_duplicate_sections=False)
        for section in self.raw_config.sections():
            self.raw_config.set(section, 'name', section)
        Server.load_config(self, reload)
        self.check_all_zserv_configs()
        try:
            self.username = self.config.defaults()['username']
            self.password = self.config.defaults()['password']
        except KeyError, e:
            es = "Could not find option %s in configuration file"
            raise ValueError(es % (str(e)))
        self.load_zservs()

    def _dispatch(self, method, params):
        if method in self.methods_requiring_authentication:
            if not self.authenticate(params[0], params[1]):
                s = "Authentication for method [%s] by user [%s] failed"
                log(s % (method, params[0]))
                raise AuthenticationError(params[0], method)
            s = "Authenticated user [%s] for method [%s]"
            log(s % (params[0], method))
        else:
            log("Method [%s] did not require authentication" % (method))
        try:
            func = getattr(self, method)
            if not type(func) == type(get_configparser):
                raise AttributeError
        except AttributeError:
            raise Exception('method "%s" is not supported' % (method))
        else:
            return func(*params)

    def authenticate(self, username, password):
        logging.getLogger('').debug('')
        return username == self.username and password == self.password

    def start_zserv(self, zserv_name):
        logging.getLogger('').debug('')
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        if self.zservs[zserv_name].pid is not None:
            raise Exception("ZServ [%s] is already running" % (zserv_name))
        self.zservs[zserv_name].start()

    def stop_zserv(self, zserv_name):
        logging.getLogger('').debug('')
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        if self.zservs[zserv_name].pid is None:
            raise Exception("ZServ [%s] is not running" % (zserv_name))
        self.zservs[zserv_name].stop()

    def restart_zserv(self, zserv_name):
        logging.getLogger('').debug('')
        self.stop_zserv(zserv_name)
        time.sleep(1)
        self.start_zserv(zserv_name)

    def start_all_zservs(self):
        logging.getLogger('').debug('')
        for zserv_name in self.zservs:
            self.start_zserv(zserv_name)

    def stop_all_zservs(self):
        logging.getLogger('').debug('')
        for zserv in [z for z in self.zservs.values() if z.pid is not None]:
            zserv.stop()

    def restart_all_zservs(self):
        logging.getLogger('').debug('')
        for zserv in [z for z in self.zservs.values() if z.pid is not None]:
            zserv.restart()

    def start(self):
        logging.getLogger('').debug('')
        self.start_all_zservs()
        return True

    def stop(self):
        logging.getLogger('').debug('')
        self.stop_all_zservs()
        return True

    def _get_zserv(self, zserv_name):
        logging.getLogger('').debug('')
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        return self.zservs[zserv_name]

    def _get_player(self, zserv_name, player_name):
        logging.getLogger('').debug('')
        zserv = self._get_zserv(zserv_name)
        if player_name not in zserv.players:
            raise ValueError("Player [%s] not found" % (player_name))
        return zserv.players[player_name]

    def _get_team(self, zserv_name, team_color):
        zserv = self._get_zserv(zserv_name)
        if not hasattr(zserv, 'teams'):
            raise Exception("%s is not a team server" % (zserv_name))
        if team_color not in zserv.teams:
            raise ValueError("Team [%s] not found" % (team_color))
        return zserv.teams[team_color]

    def get_zserv(self, zserv_name):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).export()

    def get_all_zservs(self):
        logging.getLogger('').debug('')
        return [self.get_zserv(x) for x in self.zservs]

    def list_zserv_names(self):
        logging.getLogger('').debug('')
        return self.zservs.keys()

    def _items_to_section(self, name, items):
        return '[%s]\n' % (name) + '\n'.join(["%s: %s" % x for x in items])

    def get_zserv_config(self, zserv_name):
        logging.getLogger('').debug('')
        self._get_zserv(zserv_name)
        return self._items_to_section(zserv_name,
                                      self.raw_config.items(zserv_name))

    def set_zserv_config(self, zserv_name, data):
        logging.getLogger('').debug('')
        self._get_zserv(zserv_name)

    def get_player(self, zserv_name, player_name):
        logging.getLogger('').debug('')
        return self._get_player(zserv_name, player_name).export()

    def get_all_players(self, zserv_name):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).players.export()

    def list_player_names(self, zserv_name):
        logging.getLogger('').debug('')
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        return self._get_zserv(zserv_name).players.keys()

    def get_team(self, zserv_name, team_color):
        logging.getLogger('').debug('')
        return self._get_team(zserv_name, team_color).export()

    def get_all_teams(self, zserv_name):
        logging.getLogger('').debug('')
        self._get_zserv(zserv_name)
        return self.zservs[zserv_name].teams.export()

    def get_current_map(self, zserv_name):
        logging.getLogger('').debug('')
        zserv = self._get_zserv(zserv_name)
        if zserv.map:
            return zserv.map.export()
        else:
            return None

    def get_remembered_stats(self, zserv_name, back=1):
        logging.getLogger('').debug('')
        zserv = self._get_zserv(zserv_name)
        slots = zserv.memory_slots
        if back > slots:
            raise IndexError("%d exceeds memory slots [%d]" % (back, slots))
        return zserv.remembered_stats[-back].export()

    def get_all_remembered_stats(self, zserv_name):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).remembered_stats.export()

    def send_to_zserv(self, zserv_name, message):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).send_to_zserv(message)

    def addban(self, zserv_name, ip_address, reason='rofl'):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zaddban(ip_address, reason)

    def addbot(self, zserv_name, bot_name=None):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zaddbot(bot_name)

    def addmap(self, zserv_name, map_number):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zaddmap(map_number)

    def clearmaplist(self, zserv_name):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zclearmaplist()

    def get(self, zserv_name, variable_name):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zget(variable_name)

    def kick(self, zserv_name, player_number, reason='rofl'):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zkick(player_number, reason)

    def killban(self, zserv_name, ip_address):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zkillban(ip_address)

    def map(self, zserv_name, map_number):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zmap(map_number)

    def maplist(self, zserv_name):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zmaplist()

    def players(self, zserv_name):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zplayers()

    def removebots(self, zserv_name):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zremovebots()

    def resetscores(self, zserv_name):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zresetscores()

    def say(self, zserv_name, message):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zsay(message)

    def set(self, zserv_name, variable_name, variable_value):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zset(variable_name, variable_value)

    def toggle(self, zserv_name, boolean_variable):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).ztoggle(boolean_variable)

    def unset(self, zserv_name, variable_name):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zunset(variable_name)

    def wads(self, zserv_name):
        logging.getLogger('').debug('')
        return self._get_zserv(zserv_name).zwads()

    def register_functions(self):
        logging.getLogger('').debug('')
        Server.register_functions(self)
        self.rpc_server.register_function(self.start_zserv)
        self.rpc_server.register_function(self.stop_zserv)
        self.rpc_server.register_function(self.restart_zserv)
        self.rpc_server.register_function(self.start_all_zservs)
        self.rpc_server.register_function(self.stop_all_zservs)
        self.rpc_server.register_function(self.restart_all_zservs)
        self.rpc_server.register_function(self.get_zserv)
        self.rpc_server.register_function(self.get_all_zservs)
        self.rpc_server.register_function(self.list_zserv_names)
        self.rpc_server.register_function(self.get_remembered_stats)
        self.rpc_server.register_function(self.get_all_remembered_stats)
        self.rpc_server.register_function(self.get_current_map)
        self.rpc_server.register_function(self.get_team)
        self.rpc_server.register_function(self.get_all_teams)
        self.rpc_server.register_function(self.get_player)
        self.rpc_server.register_function(self.get_all_players)
        self.rpc_server.register_function(self.list_player_names)
        self.rpc_server.register_function(self.send_to_zserv)
        self.rpc_server.register_function(self.addban)
        self.rpc_server.register_function(self.addbot)
        self.rpc_server.register_function(self.addmap)
        self.rpc_server.register_function(self.clearmaplist)
        self.rpc_server.register_function(self.get)
        self.rpc_server.register_function(self.kick)
        self.rpc_server.register_function(self.killban)
        self.rpc_server.register_function(self.map)
        self.rpc_server.register_function(self.maplist)
        self.rpc_server.register_function(self.players)
        self.rpc_server.register_function(self.removebots)
        self.rpc_server.register_function(self.resetscores)
        self.rpc_server.register_function(self.say)
        self.rpc_server.register_function(self.set)
        self.rpc_server.register_function(self.toggle)
        self.rpc_server.register_function(self.unset)
        self.rpc_server.register_function(self.wads)

