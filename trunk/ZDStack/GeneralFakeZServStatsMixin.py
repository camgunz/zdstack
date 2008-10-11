import time
import os.path
import logging

from threading import Timer

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
from ZDStack.LogListener import GeneralLogListener

class GeneralFakeZServStatsMixin:

    """GeneralZServStatsMixin adds statistics to a ZServ."""

    def __init__(self, memory_slots, player_class=BasePlayer,
                                     map_class=BaseMap,
                                     stats_class=BaseStats,
                                     log_type='server'):
        """Initializes a GeneralZServStatsMixin.

        memory_slots: an int representing the # of maps to remember
        player_class: the player class to use
        map_class:    the map class to use
        stats_class:  the stats class to use
        load_plugins: a boolean that, if True, will load plugins
        log_type:     specifies which type of log to parse, valid
                      options are "server" and "client"

        """
        logging.debug('')
        self.map_class = map_class
        self.player_class = player_class
        self.stats_class = stats_class
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
                e = {'name': '', 'number': '', 'index': 0}
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
        self.extra_exportables_funcs.append((add_players, [], {}))
        self.extra_exportables_funcs.append((add_map, [], {}))
        self.extra_exportables_funcs.append((add_remembered_slots, [], {}))
        general_log_parser = GeneralLogParser(log_type=self.log_type)
        self.general_log = LogFile('general', general_log_parser, self)
        self.general_log_listener = GeneralLogListener(self)
        self.general_log.listeners = [self.general_log_listener]
        logging.getLogger('').debug("Listeners: [%s]" % (self.general_log.listeners))
        for listener in self.general_log.listeners:
            logging.getLogger('').debug("Starting %s" % (listener))
            listener.start()
        self.set_general_log_filename()
        self.general_log.start()
        logging.getLogger('').info('Added Stats Mixin')

    def initialize_general_stats(self):
        """Initializes a ZServ's stats."""
        logging.getLogger('').debug('')
        self.map = None
        self.players = Listable()
        self.disconnected_players = Listable()
        self.should_remember = False

    def get_general_log_filename(self, roll=False):
        """Generates the general log filename."""
        logging.getLogger('').debug('')
        return os.path.join(self.homedir, 'gen' + get_logfile_suffix())

    def set_general_log_filename(self, roll=False):
        """Sets the general log filename.

        roll:  a boolean that, if given, does the following:
                - If the time is 11pm, generates a logfile name for
                  the upcoming day.
                - Does not seek to the end of a file before parsing it
                  for events (if it exists).
               Otherwise, the name generated is for the current day,
               and the ZServ's LogFile will seek to the end of its
               file (if it exists).
        """
        logging.getLogger('').debug('')
        general_log_filename = self.get_general_log_filename(roll=roll)
        self.general_log.set_filepath(general_log_filename,
                                      seek_to_end=not roll)

    def dump_stats(self):
        """Returns a list of exported stats."""
        logging.getLogger('').debug('')
        return [self.map.export(), self.players.export()]

    def save_current_general_stats(self):
        """Saves stats for the current or most recent game."""
        logging.getLogger('').debug('')
        if not (self.should_remember and self.map):
            return
        logging.getLogger('').debug('Saving stats')
        self.should_remember = False
        if len(self.remembered_stats) == self.memory_slots:
            self.remembered_stats = Listable(self.remembered_stats[1:])
        stats = self.stats_class(*self.dump_stats())
        self.remembered_stats.append(stats)

    def add_player(self, ip_address, port):
        """Adds a player to self.players

        ip_address: a string representing a player's IP address
        port: a string representing a player's port

        """
        s = "Adding player: [%s:%s]" % (ip_address, port)
        logging.getLogger('').info(s)
        ###
        # Players are uniquely identified by the combination of the IP address
        # and port number, but identity is about as far as that uniqueness
        # goes.  If players have the same name, there's no reliable way to tell
        # who fragged whom and with what.
        ###
        player = self.player_class(self, ip_address, port)
        if player not in self.players:
            s = "players pre-add: [%s]"
            # logging.getLogger('').info(s % (self.players))
            self.players.append(player)
            s = "players post-add: [%s]"
            # logging.getLogger('').info(s % (self.players))
        else:
            s = "[%s] already exists"
            # logging.getLogger('').info(s % (player_name))
            if player in self.disconnected_players:
                self.disconnected_players = \
                    [x for x in self.disconnected_players if x != player]
            player.disconnected = False
        self.update_player_numbers_and_ips()

    def remove_player(self, player_name):
        """Disconnects a player.

        player_name: the name of the player to disconnect
        
        """
        logging.getLogger('').debug('')
        player = self.player_class(player_name, self)
        player.disconnected = True
        if player in self.players:
            if player not in self.disconnected_players:
                self.disconnected_players.append(player)
        self.update_player_numbers_and_ips()

    def get_player(self, name=None, ip_address_and_port=None):
        """Returns a Player instance.

        name: the name of the player to return
        ip_address_and_port: A 2-Tuple (ip_address, port), both strings

        Either name or ip_address_and_port is optional, but at least
        one must be given.  Note that only giving name can potentially
        return the wrong player, as multiple players can have the same
        name.

        """
        logging.getLogger('').debug('')
        if ip_address_and_port:
            ip_address, port = ip_address_and_port
        else:
            ip_address, port = (None, None)
        if name and ip_address:
            cf = lambda x: x.name == name and \
                           x.ip == ip_address and \
                           x.port == port
        elif name:
            cf = lambda x: x.name == name
        elif ip_address:
            cf = lambda x: x.ip == ip_address and x.port == port
        else:
            raise ValueError("One of name or ip_address_and_port is required")
        for player in self.players:
            if cf(player):
                return player
        # Maybe we should make custom exceptions like PlayerNotFoundError
        raise ValueError("Player [%s] not found" % (name))

    def distill_player(self, possible_player_names):
        """Discerns the most likely existing player.

        possible_player_names: a list of strings representing possible
                               player names

        Because messages are formatted in such a way that separating
        messenger's name from the message is not straightforward, this
        method will return the most likely player name from a list of
        possible messenger names.  This method has other uses, but
        that's the primary one.

        """
        messenger = None
        names = [x.name for x in self.players]
        for player_name in possible_player_names:
            if player_name in names:
                messenger = self.get_player(player_name)
                break
        if not messenger:
            player_names = ', '.join(names)
            ppn = ', '.join(possible_player_names)
            logging.getLogger('').debug("No player could be distilled")
            logging.getLogger('').debug("Players: [%s]" % (player_names))
            logging.getLogger('').debug("Possible: [%s]" % (ppn))
        return messenger

    def get_player_ip_address(self, player_name):
        """Returns a player's IP address.
        
        player_name: a string representing the name of the player
                     whose IP address is to be returned

        """
        ###
        # We'll try and go on without this stuff
        ###
        d = [x for x in self.zplayers() if x['player_name'] == player_name]
        if not d:
            raise ValueError("Player [%s] not found" % (player_name))
        return d[0]['player_ip']

    def get_player_number(self, player_name):
        """Returns a player's number.
        
        player_name: a string representing the name of the player
                     whose number is to be returned
        
        This number is the same as the number indicated by the zserv
        'players' command, useful for kicking and not much else.

        """
        d = [x for x in self.zplayers() if x['player_name'] == player_name]
        if not d:
            raise ValueError("Player [%s] not found" % (player_name))
        return d[0]['player_num']

    def update_player_numbers_and_ips(self):
        """Sets player numbers and IP addresses.

        This method needs to be run upon every connection and
        disconnection if numbers and names are to remain in sync.

        """
        ###
        # We'll try and go on without this stuff and see how it goes
        ###
        return
        for d in self.zplayers():
            try:
                p = self.get_player(ip_address_and_port=(d['player_ip'],
                                                         d['player_port']))
            except ValueError:
                continue
            p.set_name(d['player_name'])
            p.number = d['player_num']

    def handle_message(self, message, messenger):
        """Handles a message.

        message:   a string representing the message
        messenger: a string representing the name of the messenger

        """
        ###
        # This is handled by plugins now, someday I'll fully remove the
        # references to this.
        ###
        pass

    def change_map(self, map_number, map_name):
        """Handles a map change event.

        map_number: an int representing the number of the new map
        map_name:   a string representing the name of the new map

        """
        logging.getLogger('').debug('')
        self.save_current_general_stats()
        self.map = self.map_class(map_number, map_name)
        self.players = [x for x in self.players \
                            if x not in self.disconnected_players]
        for player in self.players:
            player.initialize()
            player.set_map(self.map)
        self.disconnected_players = Listable()

