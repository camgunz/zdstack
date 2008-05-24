import os.path

from ZDStack import log, debug
from ZDStack.Utils import get_logfile_suffix
from ZDStack.LogFile import LogFile
from ZDStack.Dictable import Dictable
from ZDStack.Listable import Listable
from ZDStack.BaseMap import BaseMap
from ZDStack.BaseStats import BaseStats
from ZDStack.BaseZServ import BaseZServ
from ZDStack.BasePlayer import BasePlayer
from ZDStack.LogParser import GeneralLogParser
from ZDStack.LogListener import GeneralLogListener

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
            plugins = [x.strip() for x in self.config['plugins'].split(',')]
            self.plugins = plugins
        else:
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
        debug("Added Stats Mixin")

    def initialize_general_stats(self):
        debug()
        self.map = None
        self.players = Dictable()
        self.disconnected_players = Dictable()
        self.should_remember = False

    def initialize_general_log(self):
        debug()
        general_log_parser = GeneralLogParser(log_type=self.log_type)
        self.general_log = LogFile('general', general_log_parser, self)
        self.general_log_listener = GeneralLogListener(self)
        self.general_log.listeners = [self.general_log_listener]
        if self.load_plugins and self.plugins:
            self.plugin_log_listener = PluginLogListener(self, self.plugins)
            self.general_log.listeners.append(self.plugin_log_listener)
        self.general_log_listener.start()
        self.set_general_log_filename()
        self.general_log.start()

    def start_collecting_general_stats(self):
        debug()
        self.initialize_general_stats()
        self.initialize_general_log()

    def stop_collecting_general_stats(self):
        debug()
        self.general_log.stop()
        for listener in self.general_log.listeners:
            listener.stop()

    def get_general_log_filename(self, roll=False):
        debug()
        return os.path.join(self.homedir, 'gen' + get_logfile_suffix())

    def set_general_log_filename(self, roll=False):
        debug()
        general_log_filename = self.get_general_log_filename(roll=roll)
        self.general_log.set_filepath(general_log_filename,
                                      seek_to_end=not roll)

    def dump_stats(self):
        debug()
        return [self.map.export(), self.players.export()]

    def save_current_general_stats(self):
        if not self.should_remember:
            return
        self.should_remember = False
        if len(self.remembered_stats) == self.memory_slots:
            self.remembered_stats = Listable(self.remembered_stats[1:])
        if self.map:
            stats = self.stats_class(*self.dump_stats())
            self.remembered_stats.append(stats)

    def add_player(self, player_name):
        debug("player: [%s]" % (player_name))
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
            debug(s % (self.players))
            self.players[player.name] = player
            s = "players post-add: [%s]"
            debug(s % (self.players))
        else:
            s = "[%s] already exists"
            debug(s % (player_name))
            if player.name in self.disconnected_players:
                del self.disconnected_players[player.name]
            self.players[player.name].disconnected = False

    def remove_player(self, player_name):
        debug()
        player = self.player_class(player_name, self)
        if player_name in self.players:
            self.disconnected_players[player_name] = player
            self.players[player_name].disconnected = True

    def get_player(self, name):
        debug()
        if name not in self.players:
            # Maybe we should make custom exceptions like PlayerNotFoundError
            raise ValueError("Player [%s] not found" % (name))
        return self.players[name]

    def handle_message(self, message, possible_player_names):
        ###
        # I think the way this will work is we will check the messager's
        # homogenized name against some list of messagers and regexp pairs.
        # Then, we can take a specific action like "kick" or "say".  So,
        # something like:
        #
        # mionicd: "^no$" kick
        #
        ###
        debug()
        messager = None
        for player_name in possible_player_names:
            if player_name in self.players:
                messager = self.players[player_name]
                break
        if messager is None:
            es = "Received a message but none of the players existed: [%s]"
            log(es % (', '.join(possible_player_names)))
        else:
            message = message.replace(messager.name, '', 1)[3:]
            es = "Received a message [%s] from player [%s]"
            log(es % (message, messager.name))
            ###
            # Here we would do the lookup
            ###
            pass

    def change_map(self, map_number, map_name):
        debug()
        self.save_current_general_stats()
        self.map = self.map_class(map_number, map_name)
        for player_name, player in self.players.items():
            if player_name in self.disconnected_players:
                del self.players[player_name]
            else:
                player.initialize()
                player.set_map(self.map)
        self.disconnected_players = Dictable()

