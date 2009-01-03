import time
import logging

from datetime import datetime
from threading import Lock
from StringIO import StringIO

from ZDStack import get_configfile, get_configparser
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

    """Stack represents the main ZDStack class."""

    def __init__(self, config_file=None, debugging=False):
        """Initializes a Stack instance.

        config_file: optional, a string representing the path to a
                     configuration file.  If not given, looks for a
                     configuration file in a predefined list of
                     locations.
        debugging:   a boolean, whether or not debugging is enabled

        """
        self.spawn_lock = Lock()
        self.zservs = {}
        self.start_time = datetime.now()
        Server.__init__(self, config_file, debugging)
        self.methods_requiring_authentication.append('start_zserv')
        self.methods_requiring_authentication.append('stop_zserv')
        self.methods_requiring_authentication.append('start_all_zservs')
        self.methods_requiring_authentication.append('stop_all_zservs')

    def check_all_zserv_configs(self):
        """Ensures that all ZServ configuration sections are correct."""
        # logging.debug('')
        for section in self.config.sections():
            self.check_zserv_config(dict(self.config.items(section)))

    def check_zserv_config(self, zserv_config):
        """Ensures that a ZServ configuration section is correct.
        
        A dict containing ZServ configuration options and values.
        
        """
        # logging.debug('')
        if not 'type' in zserv_config:
            es = "Could not determine type of server [%s]"
            raise ValueError(es % (section))
        if zserv_config['type'].lower() not in \
                                    ('ctf', 'coop', 'duel', 'ffa', 'teamdm'):
            es = "Invalid server type [%s]"
            raise ValueError(es % (zserv_config['type']))

    def load_zservs(self):
        """Instantiates all configured ZServs."""
        # logging.debug('')
        for zserv_name in self.config.sections():
            zs_config = dict(self.config.items(zserv_name))
            if zserv_name in self.zservs:
                logging.info("Reloading Config for [%s]" % (zserv_name))
                self.zservs[zserv_name].reload_config(zs_config)
            else:
                game_mode = zs_config['type'].lower()
                memory_slots = int(zs_config['maps_to_remember'])
                log_ips = yes(zs_config['enable_ip_logging'])
                load_plugins = yes(zs_config['load_plugins'])
                zs_class = get_zserv_class(game_mode, memory_slots,
                                           log_ips, load_plugins)
                zs = zs_class(zserv_name, zs_config, self)
                # logging.debug("Adding zserv [%s]" % (zserv_name))
                self.zservs[zserv_name] = zs

    def load_config(self, reload=False):
        """Loads the configuration.

        reload: a boolean, whether or not the configuration is being
                reloaded.

        """
        # logging.debug('')
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
        """This should actually be monkeypatched into XMLRPCServer."""
        if method in self.methods_requiring_authentication:
            if not self.authenticate(params[0], params[1]):
                s = "Authentication for method [%s] by user [%s] failed"
                logging.info(s % (method, params[0]))
                raise AuthenticationError(params[0], method)
            s = "Authenticated user [%s] for method [%s]"
            logging.info(s % (params[0], method))
        else:
            s = "Method [%s] did not require authentication"
            logging.info(s % (method))
        try:
            func = getattr(self, method)
            if not type(func) == type(get_configparser):
                raise AttributeError
        except AttributeError:
            raise Exception('method "%s" is not supported' % (method))
        else:
            return func(*params)

    def authenticate(self, username, password):
        """Returns True if a user authenticates successfully.

        username: a string representing the user's username
        password: a string representing the user's password

        """
        # logging.debug('')
        return username == self.username and password == self.password

    def start_zserv(self, zserv_name):
        """Starts a ZServ.

        zserv_name: a string representing the name of a ZServ to start

        """
        # logging.debug('')
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        if self.zservs[zserv_name].pid is not None:
            raise Exception("ZServ [%s] is already running" % (zserv_name))
        self.zservs[zserv_name].start()

    def stop_zserv(self, zserv_name):
        """Stops a ZServ.

        zserv_name: a string representing the name of a ZServ to stop

        """
        # logging.debug('')
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        if self.zservs[zserv_name].pid is None:
            raise Exception("ZServ [%s] is not running" % (zserv_name))
        self.zservs[zserv_name].stop()

    def restart_zserv(self, zserv_name):
        """Restarts a ZServ.

        zserv_name: a string representing the name of a ZServ to
                    restart

        """
        # logging.debug('')
        self.stop_zserv(zserv_name)
        time.sleep(1)
        self.start_zserv(zserv_name)

    def start_all_zservs(self):
        """Starts all ZServs."""
        # logging.debug('')
        for zserv_name in self.zservs:
            self.start_zserv(zserv_name)

    def stop_all_zservs(self):
        """Stops all ZServs."""
        # logging.debug('')
        for zserv in [z for z in self.zservs.values() if z.pid is not None]:
            zserv.stop()

    def restart_all_zservs(self):
        """Restars all ZServs."""
        # logging.debug('')
        for zserv in [z for z in self.zservs.values() if z.pid is not None]:
            zserv.restart()

    def start(self):
        """Starts this Stack."""
        # logging.debug('')
        self.start_all_zservs()
        return True

    def stop(self):
        """Stops this Stack."""
        # logging.debug('')
        self.stop_all_zservs()
        return True

    def _get_zserv(self, zserv_name):
        """Returns a ZServ instance.
        
        zserv_name: a string representing the name of the ZServ to
                    return
        
        """
        # logging.debug('')
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        return self.zservs[zserv_name]

    def _get_player(self, zserv_name, player_name):
        """Returns a Player instance.

        zserv_name:  a string representing the name of the ZServ in
                     which to look for the player
        player_name: a string representing the name of the Player to
                     return

        """
        # logging.debug('')
        zserv = self._get_zserv(zserv_name)
        players = [x for x in zserv.players if x.name == player_name]
        if not players:
            raise ValueError("Player [%s] not found" % (player_name))
        return players[0]

    def _get_team(self, zserv_name, team_color):
        """Returns a Team instance.

        zserv_name: a string representing the name of the ZServ in
                    which to look for the team
        team_color: a string representing the color of the Team to
                    return

        """
        zserv = self._get_zserv(zserv_name)
        if not hasattr(zserv, 'teams'):
            raise Exception("%s is not a team server" % (zserv_name))
        if team_color not in zserv.teams:
            raise ValueError("Team [%s] not found" % (team_color))
        return zserv.teams[team_color]

    def get_zserv(self, zserv_name):
        """Returns an marshallable representation of a ZServ.

        zserv_name: the name of the ZServ to get

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).export()

    def get_all_zservs(self):
        """Returns all ZServs in marshallable representations."""
        # logging.debug('')
        return [self.get_zserv(x) for x in self.zservs]

    def list_zserv_names(self):
        """Returns a list of ZServ names."""
        # logging.debug('')
        return self.zservs.keys()

    def _items_to_section(self, name, items):
        """Converts a list of items into a ConfigParser section.

        name:  a string representing the name of the section to
               generate
        items: a list of option, value pairs (strings).

        """
        return '[%s]\n' % (name) + '\n'.join(["%s: %s" % x for x in items])

    def get_zserv_config(self, zserv_name):
        """Returns a ZServ's configuration as a string.

        zserv_name: a string representing the ZServ's name

        """
        # logging.debug('')
        self._get_zserv(zserv_name)
        return self._items_to_section(zserv_name,
                                      self.raw_config.items(zserv_name))

    def set_zserv_config(self, zserv_name, data):
        """Sets a ZServ's config.

        zserv_name: a string representing the ZServ's name
        data:       a string representing the new configuration data

        """
        # logging.debug('')
        cp = RCP()
        sio = StringIO(data)
        cp.readfp(sio)
        main_cp = get_configparser()
        for o, v in cp.items(zserv_name):
            main_cp.set(zserv_name, o, v)
        main_cp.save()
        self.initialize_config(get_configfile(), reload=True)
        zs_config = dict(self.config.items(zserv_name))
        self._get_zserv(zserv_name).reload_config(zs_config)

    def get_player(self, zserv_name, player_name):
        """Returns a marshallable representation of a Player.

        zserv_name:  a string representing the name of the ZServ in
                     which to look for the player
        player_name: a string representing the name of the Player to
                     return

        """
        # logging.debug('')
        return self._get_player(zserv_name, player_name).export()

    def get_all_players(self, zserv_name):
        """Returns a list of marshallable representations of players.

        zserv_name: a string representing the name of the ZServ
                    from which to retrieve the players

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).players.export()

    def list_player_names(self, zserv_name):
        """Returns a list of strings representing player names.

        zserv_name: a string representing the name of the ZServ
                    from which to retrieve the names

        """
        # logging.debug('')
        if zserv_name not in self.zservs:
            raise ValueError("ZServ [%s] not found" % (zserv_name))
        players = self._get_zserv(zserv_name).players
        return [x.name for x in players if x.name]

    def get_team(self, zserv_name, team_color):
        """Returns a marshallable representation of a team.

        zserv_name: a string representing the name of the ZServ from
                    which to retrieve the team
        team_color: a string representing the color of the team to
                    retrieve

        """
        # logging.debug('')
        return self._get_team(zserv_name, team_color).export()

    def get_all_teams(self, zserv_name):
        """Returns a list of marshallable representations of all teams.

        zserv_name: a string representing the name of the ZServ from
                    which to retrieve the teams

        """
        # logging.debug('')
        self._get_zserv(zserv_name)
        return self.zservs[zserv_name].teams.export()

    def get_current_map(self, zserv_name):
        """Returns a marshallable representation of the current map.

        zserv_name: a string representing the name of the ZServ from
                    which to retrieve the map

        """
        # logging.debug('')
        zserv = self._get_zserv(zserv_name)
        if zserv.map:
            return zserv.map.export()
        else:
            return None

    def get_remembered_stats(self, zserv_name, back=1):
        """Returns a marshallable representation map stats.

        zserv_name: a string representing the name of the ZServ from
                    which to retrieve the stats
        back:       which map to retrieve, starts at/defaults to 1

        Note that remembered stats are held in a list ordered from
        least to most recent, i.e.:

          [map01, map02, map03, map04, map07]

        So a back value of 1 retrieves map07, 2 retrieves map04, etc.
        Also, the current map is not held in this list, use
        get_current_map() for that.

        """
        # logging.debug('')
        zserv = self._get_zserv(zserv_name)
        slots = zserv.memory_slots
        if back > slots:
            raise IndexError("%d exceeds memory slots [%d]" % (back, slots))
        return zserv.remembered_stats[-back].export()

    def get_all_remembered_stats(self, zserv_name):
        """Returns a list of marshallable representations of all stats.

        zserv_name: a string representing the name of the ZServ from
                    which to retrieve the stats

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).remembered_stats.export()

    def send_to_zserv(self, zserv_name, message):
        """Sends a command to a running zserv process.

        zserv_name: a string representing the name of the ZServ to
                    send the message to
        message:    a string, the message to send

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).send_to_zserv(message)

    def addban(self, zserv_name, ip_address, reason='rofl'):
        """Adds a ban.

        zserv_name: a string representing the name of the ZServ to add
                    the ban to
        ip_address: a string representing the IP address to ban
        reason:     a string representing the reason for the ban

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zaddban(ip_address, reason)

    def addbot(self, zserv_name, bot_name=None):
        """Adds a bot.

        zserv_name: a string representing the name of the ZServ to add
                    the bot to
        bot_name:   a string representing the name of the bot to add

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zaddbot(bot_name)

    def addmap(self, zserv_name, map_number):
        """Adds a map to the maplist.

        zserv_name: a string representing the name of the ZServ to add
                    the map to
        map_number: a string representing the number of the map to add

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zaddmap(map_number)

    def clearmaplist(self, zserv_name):
        """Clears the maplist.

        zserv_name: a string representing the name of the ZServ whose
                    maplist is to be cleared

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zclearmaplist()

    def get(self, zserv_name, variable_name):
        """Gets the value of a variable.

        zserv_name:    a string representing the name of the ZServ to
                       retrieve the variable value from
        variable_name: a string representing the name of the variable
                       whose value is to be retrieved

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zget(variable_name)

    def kick(self, zserv_name, player_number, reason='rofl'):
        """Kicks a player from the zserv.

        zserv_name:    a string representing the name of the ZServ to
                       kick the player from
        player_number: a string representing the number of the player
                       to kick
        reason:        a string representing the reason for the kick

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zkick(player_number, reason)

    def killban(self, zserv_name, ip_address):
        """Removes a ban.

        zserv_name: a string representing the name of the ZServ to
                    remove the ban from
        ip_address: a string representing the IP address to remove the
                    ban for

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zkillban(ip_address)

    def map(self, zserv_name, map_number):
        """Changes the current map.

        zserv_name: a string representing the name of the ZServ to
                    change the map on
        map_number: a string representing the number of the map to
                    change to

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zmap(map_number)

    def maplist(self, zserv_name):
        """Returns the maplist.

        zserv_name: a string representing the name of the ZServ to
                    retrieve the maplist for

        Returns a list of strings representing the numbers of the maps
        in the maplist.

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zmaplist()

    def players(self, zserv_name):
        """Returns a list of players and their info.

        zserv_name: a string representing the name of the ZServ to
                    list the players for

        Returns a list of strings representing the number, name, and
        IP address of all players.

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zplayers()

    def removebots(self, zserv_name):
        """Removes all bots.

        zserv_name: a string representing the name of the ZServ to
                    remove the bots from

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zremovebots()

    def resetscores(self, zserv_name):
        """Resets all scores.

        zserv_name: a string representing the name of the ZServ to
                    reset the scores for

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zresetscores()

    def say(self, zserv_name, message):
        """Sends a message from "] CONSOLE [".

        zserv_name: a string representing the name of the ZServ to
                    send the message to
        message:    a string, the message to send

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zsay(message)

    def set(self, zserv_name, variable_name, variable_value):
        """Sets the value of a variable

        zserv_name:     a string representing the name of the ZServ
        variable_name:  a string representing the name of the variable
                        to set
        variable_value: a string representing the new value of the
                        variable

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zset(variable_name, variable_value)

    def toggle(self, zserv_name, boolean_variable):
        """Toggles a boolean option.

        zserv_name:       a string representing the name of the ZServ
        boolean_variable: a string representing the name of the
                          boolean variable to toggle on or off

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).ztoggle(boolean_variable)

    def unset(self, zserv_name, variable_name):
        """Unsets a variable (removes it).

        zserv_name:    a string representing the name of the ZServ to
                       remove the variable from
        variable_name: the name of the variable to unset

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zunset(variable_name)

    def wads(self, zserv_name):
        """Returns a list of the used WADs.

        zserv_name: a string representing the name of the ZServ to add
                    the bot to

        Returns a list of strings representing the names of the used
        WADs.

        """
        # logging.debug('')
        return self._get_zserv(zserv_name).zwads()

    def register_functions(self):
        """Registers RPC functions."""
        # logging.debug('')
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
        self.rpc_server.register_function(self.get_zserv_config)
        self.rpc_server.register_function(self.set_zserv_config)
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

