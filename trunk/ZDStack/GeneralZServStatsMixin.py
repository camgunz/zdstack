import sys
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
from ZDStack.LogListener import GeneralLogListener, PluginLogListener

class GeneralZServStatsMixin:

    """GeneralZServStatsMixin adds statistics to a ZServ."""

    def __init__(self, memory_slots, player_class=BasePlayer,
                                     map_class=BaseMap,
                                     stats_class=BaseStats,
                                     load_plugins=False,
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
            d['remembered_stats'] = Listable()
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
        """Initializes a ZServ's stats."""
        # logging.getLogger('').debug('')
        self.map = None
        self.players = Listable()
        self.disconnected_players = Listable()
        self.should_remember = False

    def start_collecting_general_stats(self):
        """Starts collecting statistics."""
        # logging.getLogger('').debug('')
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
        """Stops collecting statistics."""
        # logging.getLogger('').debug('')
        self.general_log.stop()
        for listener in self.general_log.listeners:
            listener.stop()

    def get_general_log_filename(self, roll=False):
        """Generates the general log filename."""
        # logging.getLogger('').debug('')
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
        # logging.getLogger('').debug('')
        general_log_filename = self.get_general_log_filename(roll=roll)
        self.general_log.set_filepath(general_log_filename,
                                      seek_to_end=not roll)

    def dump_stats(self):
        """Returns a list of exported stats."""
        # logging.getLogger('').debug('')
        return [self.map.export(), self.players.export()]

    def save_current_general_stats(self):
        """Saves stats for the current or most recent game."""
        # logging.getLogger('').debug('')
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
        self.update_player_numbers_and_ips()
        time.sleep(.2)
        ###
        # Players are uniquely identified by the combination of the IP address
        # and port number, but identity is about as far as that uniqueness
        # goes.  If players have the same name, there's no reliable way to tell
        # who fragged whom and with what.
        blah_list = [(p.name, p.ip) for p in self.players]
        player = self.player_class(self, ip_address, port)
        if (player.name, player.ip) in blah_list:
            if player not in self.players:
                ###
                # A player has reconnected
                dp = Listable()
                for p in self.disconnected_players:
                    if (p.name, p.ip) != (player.name, player.ip):
                        dp.append(p)
                player.disconnected = False
        else:
            ###
            # A player is connecting for the first time
            self.players.append(player)
        self.update_player_numbers_and_ips()

    def remove_player(self, player_name):
        """Disconnects a player.

        player_name: the name of the player to disconnect
        
        """
        # logging.getLogger('').debug('')
        player = self.get_player(name=player_name)
        player.disconnected = True
        player.playing = False
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
        # logging.getLogger('').debug('')
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
        if name:
            raise ValueError("Player [%s] not found" % (name))
        else:
            raise ValueError("Address [%s:%s] not found" % ip_address_and_port)

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
        for d in self.zplayers():
            try:
                p = self.get_player(ip_address_and_port=(d['player_ip'],
                                                         d['player_port']))
            except ValueError, e:
                print >> sys.stderr, "ValueError in upnai: %s" % (e)
                continue
            except Exception, e:
                es = "Error updating player #s and IPs: %s"
                print >> sys.stderr, es % (e)
                continue
            p.set_name(d['player_name'])
            p.number = d['player_num']
            print >> sys.stderr, "Set name %s to address %s:%s" % (p.name, p.ip, p.port)
            print >> sys.stderr, "Set number %s to address %s:%s" % (p.number, p.ip, p.port)

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
        # logging.getLogger('').debug('')
        self.save_current_general_stats()
        self.map = self.map_class(map_number, map_name)
        self.players = [x for x in self.players \
                            if x not in self.disconnected_players]
        self.players = Listable(self.players)
        for player in self.players:
            player.initialize()
            player.set_map(self.map)
        self.disconnected_players = Listable()

    def send_to_zserv(self, message, event_response_type=None):
        """Sends a message to the running zserv process.

        message:             a string representing the message to send
        event_response_type: a string representing the type of event to
                             wait for in response

        When using this method, keep the following in mind:
            - Your message should not contain newlines.
            - If event_response_type is None, no response is returned

        This method returns a list of events returned in response.

        """
        # logging.getLogger('').debug('')
        if event_response_type is not None:
            self.general_log.watch_for_response(event_response_type)
        self.zserv.stdin.write(message.strip('\n') + '\n')
        self.zserv.stdin.flush()
        if event_response_type is not None:
            return self.general_log.get_response()

    def zaddban(self, ip_address, reason='rofl'):
        """Adds a ban.

        ip_address: a string representing the IP address to ban
        reason:     a string representing the reason for the ban

        """
        # logging.getLogger('').debug('')
        return self.send_to_zserv('addban %s %s' % (ip_address, reason),
                                  'addban_command')

    def zaddtimedban(self, duration, ip_address, reason='rofl'):
        """Adds a ban with an expiration.

        duration:   an integer representing how many minutes the ban
                    should last
        ip_address: a string representing the IP address to ban
        reason:     a string representing the reason for the ban

        """
        self.zaddban(ip_address, reason)
        seconds = duration * 60
        Timer(seconds, self.zkillban, [ip_address]).start()

    def zaddbot(self, bot_name):
        """Adds a bot.

        bot_name: a string representing the name of the bot to add.

        """
        # logging.getLogger('').debug('')
        return self.send_to_zserv('addbot %s' % (bot_name), 'addbot_command')

    def zaddmap(self, map_number):
        """Adds a map to the maplist.

        map_number: an int representing the name of the map to add

        """
        # logging.getLogger('').debug('')
        return self.send_to_zserv('addmap %s' % (map_number))

    def zclearmaplist(self):
        """Clears the maplist."""
        # logging.getLogger('').debug('')
        return self.send_to_zserv('clearmaplist')

    def zget(self, variable_name):
        """Gets a variable.

        variable_name: a string representing the name of the variable
                       to get

        """
        # logging.getLogger('').debug('')
        return self.send_to_zserv('get %s', 'get_command')

    def zkick(self, player_number, reason='rofl'):
        """Kicks a player.

        player_number: an int representing the number of the player to
                       kick
        reason:        a string representing the reason for the kick

        """
        # logging.getLogger('').debug('')
        return self.send_to_zserv('kick %s %s' % (player_number, reason))

    def zkillban(self, ip_address):
        """Removes a ban.

        ip_address: a string representing the IP address to un-ban

        """
        # logging.getLogger('').debug('')
        return self.send_to_zserv('killban %s' % (ip_address))

    def zmap(self, map_number):
        """Changes the current map.

        map_number: an int representing the number of the map to
                    change to

        """
        # logging.getLogger('').debug('')
        return self.send_to_zserv('map %s' % (map_number))

    def zmaplist(self):
        """Gets the maplist.

        Returns a list of strings representing the names of maps in
        the maplist.  An example of one of these strings is: "map01".

        """
        # logging.getLogger('').debug('')
        return self.send_to_zserv('maplist', 'maplist_command')

    def zplayers(self):
        """Returns a list of players in the server."""
        # logging.getLogger('').debug('')
        return self.send_to_zserv('players', 'players_command')

    def zremovebots(self):
        """Removes all bots."""
        # logging.getLogger('').debug('')
        return self.send_to_zserv('removebots')

    def zresetscores(self):
        """Resets all scores."""
        # logging.getLogger('').debug('')
        return self.send_to_zserv('resetscores')

    def zsay(self, message):
        """Sends a message as ] CONSOLE [.
        
        message: a string representing the message to send.
        
        """
        # logging.getLogger('').debug('')
        return self.send_to_zserv('say %s' % (message))

    def zset(self, variable_name, variable_value):
        """Sets a variable.

        variable_name:  a string representing the name of the variable
                        to set
        variable_value: a string representing the value to set the
                        variable to

        """
        # logging.getLogger('').debug('')
        s = 'set "%s" "%s"' % (variable_name, variable_value)
        return self.send_to_zserv(s)

    def ztoggle(self, boolean_variable):
        """Toggles a boolean variable.

        boolean_variable: a string representing the name of the
                          boolean variable to toggle

        """
        # logging.getLogger('').debug('')
        return self.send_to_zserv('toggle %s' % (boolean_variable))

    def zunset(self, variable_name):
        """Unsets a variable.

        variable_name: a string representing the name of the variable
                       to unset

        """
        # logging.getLogger('').debug('')
        return self.send_to_zserv('unset %s' % (variable_name))

    def zwads(self):
        """Returns a list of the wads in use."""
        # logging.getLogger('').debug('')
        return self.send_to_zserv('wads', 'wads_command')

