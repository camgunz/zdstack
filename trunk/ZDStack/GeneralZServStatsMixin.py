import time
import os.path
import logging

from ZDStack import log
from ZDStack.Utils import get_logfile_suffix
from ZDStack.LogFile import LogFile
from ZDStack.Dictable import Dictable
from ZDStack.Listable import Listable
from ZDStack.BaseMap import BaseMap
from ZDStack.BaseStats import BaseStats
from ZDStack.BaseZServ import BaseZServ
from ZDStack.BasePlayer import BasePlayer
from ZDStack.LogParser import GeneralLogParser
from ZDStack.LogListener import GeneralLogListener, PluginLogListener

class GeneralZServStatsMixin:

    def __init__(self, memory_slots, player_class=BasePlayer,
                                     map_class=BaseMap,
                                     stats_class=BaseStats,
                                     load_plugins=False,
                                     log_type='server'):
        self.map_class = map_class
        self.player_class = player_class
        self.stats_class = stats_class
        self.load_plugins = load_plugins
        if self.load_plugins and 'plugins' in self.config:
            logging.getLogger('').info("Loading plugins")
            plugins = [x.strip() for x in self.config['plugins'].split(',')]
            self.plugins = plugins
            for plugin in self.plugins:
                logging.getLogger('').info("Loaded plugin [%s]" % (plugin))
        else:
            logging.getLogger('').info("Not loading plugins")
            logging.getLogger('').debug("Load plugins: [%s]" % (load_plugins))
            logging.getLogger('').debug("Plugins: [%s]" % ('plugins' in self.config))
            self.plugins = None
        self.log_type = log_type
        self.memory_slots = memory_slots
        self.remembered_stats = Listable()
        self.initialize_general_stats()
        def add_players(d):
            d['players'] = len(self.players) - len(self.disconnected_players)
            return d
        def add_map(d):
            if not self.map:
                e = {'name': '', 'number': '',
                     'index': 0}
            else:
                e = {'name': self.map.name, 'number': self.map.number,
                     'index': 0}
            d['map'] = e
            return d
        def add_remembered_slots(d):
            d['remembered_stats'] = []
            counter = 0
            for rm in reversed(self.remembered_stats):
                counter += 1
                e = {'name': rm.name, 'number': rm.number, 'index': counter}
                d['remembered_stats'].append(e)
            return d
        f1 = (self.start_collecting_general_stats, [], {})
        f2 = (self.stop_collecting_general_stats, [], {})
        self.pre_spawn_funcs.append(f1)
        self.post_spawn_funcs.append(f2)
        self.extra_exportables_funcs.append((add_players, [], {}))
        self.extra_exportables_funcs.append((add_map, [], {}))
        self.extra_exportables_funcs.append((add_remembered_slots, [], {}))
        logging.getLogger('').info('Added Stats Mixin')

    def initialize_general_stats(self):
        logging.getLogger('').debug('')
        self.map = None
        self.players = Dictable()
        self.disconnected_players = Dictable()
        self.should_remember = False

    def start_collecting_general_stats(self):
        logging.getLogger('').debug('')
        self.initialize_general_stats()
        general_log_parser = GeneralLogParser(log_type=self.log_type)
        self.general_log = LogFile('general', general_log_parser, self)
        self.general_log_listener = GeneralLogListener(self)
        if self.load_plugins and self.plugins:
            logging.getLogger('').debug("Adding PLL to listeners")
            self.plugin_log_listener = PluginLogListener(self, self.plugins)
            self.general_log.listeners = [self.general_log_listener,
                                          self.plugin_log_listener]
        else:
            logging.getLogger('').debug("Not adding PLL to listeners")
            self.general_log.listeners = [self.general_log_listener]
        logging.getLogger('').debug("Listeners: [%s]" % (self.general_log.listeners))
        for listener in self.general_log.listeners:
            logging.getLogger('').debug("Starting %s" % (listener))
            listener.start()
        self.set_general_log_filename()
        self.general_log.start()

    def stop_collecting_general_stats(self):
        logging.getLogger('').debug('')
        self.general_log.stop()
        for listener in self.general_log.listeners:
            listener.stop()

    def get_general_log_filename(self, roll=False):
        logging.getLogger('').debug('')
        return os.path.join(self.homedir, 'gen' + get_logfile_suffix())

    def set_general_log_filename(self, roll=False):
        logging.getLogger('').debug('')
        general_log_filename = self.get_general_log_filename(roll=roll)
        self.general_log.set_filepath(general_log_filename,
                                      seek_to_end=not roll)

    def dump_stats(self):
        logging.getLogger('').debug('')
        return [self.map.export(), self.players.export()]

    def save_current_general_stats(self):
        logging.getLogger('').debug('')
        if not (self.should_remember and self.map):
            return
        logging.getLogger('').debug('Saving stats')
        self.should_remember = False
        if len(self.remembered_stats) == self.memory_slots:
            self.remembered_stats = Listable(self.remembered_stats[1:])
        stats = self.stats_class(*self.dump_stats())
        self.remembered_stats.append(stats)

    def add_player(self, player_name):
        logging.getLogger('').info("player: [%s]" % (player_name))
        ###
        # It's possible for players to have the same name, so that this
        # function will do nothing.  There's absolutely nothing we can do
        # about this, stats are just fucked for those players.  Basically, the
        # first player in line gets all the action.  In a way, it's funny
        # because a group of people could all join a server under the same
        # name, and blow up stats for a certain player.
        ###
        player = self.player_class(player_name, self)
        if player.name not in self.players:
            s = "players pre-add: [%s]"
            logging.getLogger('').info(s % (self.players))
            self.players[player.name] = player
            s = "players post-add: [%s]"
            logging.getLogger('').info(s % (self.players))
        else:
            s = "[%s] already exists"
            logging.getLogger('').info(s % (player_name))
            if player.name in self.disconnected_players:
                del self.disconnected_players[player.name]
            self.players[player.name].disconnected = False

    def remove_player(self, player_name):
        logging.getLogger('').debug('')
        player = self.player_class(player_name, self)
        if player_name in self.players:
            self.disconnected_players[player_name] = player
            self.players[player_name].disconnected = True

    def get_player(self, name):
        logging.getLogger('').debug('')
        if name not in self.players:
            # Maybe we should make custom exceptions like PlayerNotFoundError
            raise ValueError("Player [%s] not found" % (name))
        return self.players[name]

    def distill_player(self, possible_player_names):
        messenger = None
        for player_name in possible_player_names:
            if player_name in self.players:
                messenger = self.players[player_name]
                break
        if not messenger:
            player_names = ', '.join(self.players.keys())
            ppn = ', '.join(possible_player_names)
            logging.getLogger('').debug("No player could be distilled")
            logging.getLogger('').debug("Players: [%s]" % (player_names))
            logging.getLogger('').debug("Possible: [%s]" % (ppn))
        return messenger

    def handle_message(self, message, messenger):
        ###
        # I think the way this will work is we will check the messenger's
        # homogenized name against some list of messagers and regexp pairs.
        # Then, we can take a specific action like "kick" or "say".  So,
        # something like:
        #
        # mionicd: "^no$" kick
        #
        ###
        logging.getLogger('').debug('')
        if messenger is None:
            s = "Received a message but none of the players existed"
            logging.getLogger('').info(s)
        else:
            s = "Received a message [%s] from player [%s]"
            logging.getLogger('').info(s % (message, messenger.name))
        ###
        # Here we would do the lookup
        ###
        pass

    def change_map(self, map_number, map_name):
        logging.getLogger('').debug('')
        self.save_current_general_stats()
        self.map = self.map_class(map_number, map_name)
        for player_name, player in self.players.items():
            if player_name in self.disconnected_players:
                del self.players[player_name]
            else:
                player.initialize()
                player.set_map(self.map)
        self.disconnected_players = Dictable()

    def send_to_zserv(self, message, event_response_type=None):
        logging.getLogger('').debug('')
        if event_response_type is not None:
            self.general_log.watch_for_response(event_response_type)
        self.zserv.stdin.write(message + '\n')
        self.zserv.stdin.flush()
        if event_response_type is not None:
            return self.general_log.get_response()

    def zaddban(self, ip_address, reason='rofl'):
        logging.getLogger('').debug('')
        return self.send_to_zserv('addban %s %s' % (ip_address, reason),
                                  'addban_command')

    def zaddbot(self, bot_name=None):
        logging.getLogger('').debug('')
        return self.send_to_zserv('addbot %s' % (bot_name), 'addbot_command')

    def zaddmap(self, map_number):
        logging.getLogger('').debug('')
        return self.send_to_zserv('addmap %s' % (map_number))

    def zclearmaplist(self):
        logging.getLogger('').debug('')
        return self.send_to_zserv('clearmaplist')

    def zget(self, variable_name):
        logging.getLogger('').debug('')
        return self.send_to_zserv('get %s', 'get_command')

    def zkick(self, player_number, reason='rofl'):
        logging.getLogger('').debug('')
        return self.send_to_zserv('kick %s %s' % (player_number, reason))

    def zkillban(self, ip_address):
        logging.getLogger('').debug('')
        return self.send_to_zserv('killban %s' % (ip_address))

    def zmap(self, map_number):
        logging.getLogger('').debug('')
        return self.send_to_zserv('map %s' % (map_number))

    def zmaplist(self):
        logging.getLogger('').debug('')
        return self.send_to_zserv('maplist', 'maplist_command')

    def zplayers(self):
        logging.getLogger('').debug('')
        return self.send_to_zserv('players', 'players_command')

    def zremovebots(self):
        logging.getLogger('').debug('')
        return self.send_to_zserv('removebots')

    def zresetscores(self):
        logging.getLogger('').debug('')
        return self.send_to_zserv('resetscores')

    def zsay(self, message):
        logging.getLogger('').debug('')
        return self.send_to_zserv('say %s' % (message))

    def zset(self, variable_name, variable_value):
        logging.getLogger('').debug('')
        s = 'set "%s" "%s"' % (variable_name, variable_value)
        return self.send_to_zserv(s)

    def ztoggle(self, boolean_variable):
        logging.getLogger('').debug('')
        return self.send_to_zserv('toggle %s' % (boolean_variable))

    def zunset(self, variable_name):
        logging.getLogger('').debug('')
        return self.send_to_zserv('unset %s' % (variable_name))

    def zwads(self):
        logging.getLogger('').debug('')
        return self.send_to_zserv('wads', 'wads_command')


