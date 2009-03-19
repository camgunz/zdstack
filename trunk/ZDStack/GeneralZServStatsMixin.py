from __future__ import with_statement

import sys
import time
import os.path
import logging

from ZDStack import PlayerNotFoundError
from ZDStack.Utils import yes
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

    def __init__(self, config):
        """Initializes a GeneralZServStatsMixin."""

    def _add_player(self, player, acquire_lock=True):
        """Adds a player to self.players - threadsafe.

        player:       a Player instance
        acquire_lock: if True, will acquire self._players_lock before
                      taking any action; True by default

        """
        def blah():
            full_list = []
            name_list = []
            p_full = (player.name, player.ip, player.port)
            p_name = (player.name, player.ip)
            for p in self.players:
                full_list.append((p.name, p.ip, p.port))
                name_list.append((p.name, p.ip))
            if p_name in name_list:
                ###
                # Player reconnected
                #
                # Recreate self.disconnected_players without this player
                # Find this player in self.players and:
                #   set .port to new port
                #   set .disconnected to False
                ###
                logging.debug("Player [%s] has reconnected" % (p_name[0]))
                dp = Listable([x for x in self.disconnected_players \
                                            if (x.name, x.ip) != p_name])
                self.disconnected_players = dp
                for p in self.players:
                    if (p.name, p.ip) == p_name:
                        p.port = player.port
                        p.disconnected = False
            else:
                ###
                # Totally new connection
                ###
                logging.debug("Found totally new player [%s]" % (p_name[0]))
                self.players.append(player)
        if acquire_lock:
            with self._players_lock:
                blah()
        else:
            blah()

    def _remove_player(self, player, acquire_lock=True):
        """Disconnects a player - threadsafe.

        player:       a Player instance
        acquire_lock: if True, will acquire self._players_lock before
                      taking any action; True by default

        """
        def blah():
            player.playing = False
            player.disconnected = True
            if player in self.players and \
               player not in self.disconnected_players:
                self.disconnected_players.append(player)
        if acquire_lock:
            with self._players_lock:
                blah()
        else:
            blah()

    def sync_players(self, sleep=None):
        """Ensures that self.players matches up with self.zplayers().
        
        sleep: a float representing how much time to sleep between
               acquiring the _players_lock and creating the list of
               players; default to not sleeping at all (None)
               
        """
        zplayers = self.zplayers()
        with self._players_lock:
            if sleep:
                time.sleep(sleep)
            players_list = []
            disconnected_players_list = []
            zplayers_list = []
            zplayers_list_plus_numbers = []
            for p in self.players:
                if not p.name:
                    ###
                    # Skip players w/ blank names
                    ###
                    continue
                players_list.append((p.name, p.ip, p.port))
            for dp in self.disconnected_players:
                if not dp.name:
                    ###
                    # Skip players w/ blank names
                    ###
                    continue
                disconnected_players_list.append((dp.name, dp.ip, dp.port))
            for d in zplayers:
                if not d['player_name']:
                    ###
                    # Skip players w/ blank names
                    ###
                    continue
                zplayers_list.append((d['player_name'], d['player_ip'],
                                      d['player_port']))
                zplayers_list_plus_numbers.append((d['player_num'],
                                                   d['player_name'],
                                                   d['player_ip'],
                                                   d['player_port']))
            for z_full in zplayers_list:
                if z_full not in players_list or \
                   z_full in disconnected_players_list:
                    ###
                    # found a missing or reconnected player
                    ###
                    player = self.player_class(self, z_full[1], z_full[2],
                                               z_full[0])
                    self._add_player(player, acquire_lock=False)
                    logging.debug("Added new player [%s]" % (player.name))
            for p_full in players_list:
                if p_full not in zplayers_list: # found a ghost player
                    player = self.get_player(name=p_full[0],
                                             ip_address_and_port=p_full[1:])
                    logging.debug("Removed player [%s]" % (p_full[0]))
                    self._remove_player(player, acquire_lock=False)
            for z_full_num in zplayers_list_plus_numbers:
                for p in self.players:
                    if (p.name, p.ip, p.port) == z_full_num[1:]:
                        if p.number != z_full_num[0]:
                            if p.name.endswith('s'):
                                es = "Set %s' number to %s"
                            else:
                                es = "Set %s's number to %s"
                            logging.debug(es % (p.name, z_full_num[0]))
                            p.number = z_full_num[0]

    def add_player(self, ip_address, port):
        """Adds a player to self.players

        ip_address: a string representing a player's IP address
        port: a string representing a player's port

        """
        s = "Adding player: [%s:%s]" % (ip_address, port)
        logging.debug(s)
        self.update_player_numbers_and_ips()
        time.sleep(.2)
        ###
        # Players are uniquely identified by the combination of the IP address
        # and port number, but identity is about as far as that uniqueness
        # goes.  If players have the same name, there's no reliable way to tell
        # who fragged whom and with what.
        player = self.player_class(self, ip_address, port)
        self._add_player(player)
        self.update_player_numbers_and_ips()

    def remove_player(self, player_name):
        """Disconnects a player.

        player_name: the name of the player to disconnect
        
        """
        # logging.debug('')
        player = self.get_player(name=player_name)
        self._remove_player(player)
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
        # logging.debug('')
        if name and ip_address_and_port:
            ip_address, port = ip_address_and_port
            cf = lambda x: x.name == name and \
                           x.ip == ip_address and \
                           x.port == port
        elif name:
            cf = lambda x: x.name == name
        elif ip_address_and_port:
            ip_address, port = ip_address_and_port
            cf = lambda x: x.ip == ip_address and x.port == port
        else:
            raise ValueError("One of name or ip_address_and_port is required")
        for player in self.players:
            if cf(player):
                return player
        self.sync_players()
        for player in self.players:
            if cf(player):
                return player
        raise PlayerNotFoundError(name, ip_address_and_port)

    def update_player_numbers_and_ips(self):
        """Sets player numbers and IP addresses.

        This method needs to be run upon every connection and
        disconnection if numbers and names are to remain in sync.

        """
        for d in self.zplayers():
            try:
                p = self.get_player(ip_address_and_port=(d['player_ip'],
                                                         d['player_port']))
            except PlayerNotFoundError, pnfe:
                es = "Players out of sync, %s at %s:%s not found"
                logging.debug(es % (d['player_name'], d['player_ip'],
                                    d['player_port']))
                continue
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
        def blah():
            for player_name in possible_player_names:
                if player_name in names:
                    return self.get_player(name=player_name)
        messenger = blah()
        if not messenger:
            self.sync_players()
            names = [x.name for x in self.players]
            messenger = blah()
        # if not messenger:
        #     player_names = ', '.join(names)
        #     ppn = ', '.join(possible_player_names)
        #     logging.info("No player could be distilled")
        #     logging.info("Players: [%s]" % (player_names))
        #     logging.info("Possible: [%s]" % (ppn))
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
        # logging.debug('')
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
            - Your message cannot contain newlines.
            - If event_response_type is None, no response will be
              returned

        This method returns a list of events returned in response.

        """
        # logging.debug('')
        if '\n' in message or '\r' in message:
            es = "Message cannot contain newlines or carriage returns"
            raise ValueError(es)
        with self._zserv_stdin_lock:
            ###
            # zserv's STDIN is (obviously) not threadsafe, so we need to ensure
            # that access to it is limited to 1 thread at a time, which is both
            # writing to it, and waiting for responses from its STDOUT.
            ###
            if event_response_type is not None:
                self.general_log.watch_for_response(event_response_type)
            self.zserv.stdin.write(message + '\n')
            self.zserv.stdin.flush()
            if event_response_type is not None:
                return self.general_log.get_response()

    def zaddban(self, ip_address, reason='rofl'):
        """Adds a ban.

        ip_address: a string representing the IP address to ban
        reason:     a string representing the reason for the ban

        """
        # logging.debug('')
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
        # logging.debug('')
        return self.send_to_zserv('addbot %s' % (bot_name), 'addbot_command')

    def zaddmap(self, map_number):
        """Adds a map to the maplist.

        map_number: an int representing the name of the map to add

        """
        # logging.debug('')
        return self.send_to_zserv('addmap %s' % (map_number))

    def zclearmaplist(self):
        """Clears the maplist."""
        # logging.debug('')
        return self.send_to_zserv('clearmaplist')

    def zget(self, variable_name):
        """Gets a variable.

        variable_name: a string representing the name of the variable
                       to get

        """
        # logging.debug('')
        return self.send_to_zserv('get %s', 'get_command')

    def zkick(self, player_number, reason='rofl'):
        """Kicks a player.

        player_number: an int representing the number of the player to
                       kick
        reason:        a string representing the reason for the kick

        """
        # logging.debug('')
        return self.send_to_zserv('kick %s %s' % (player_number, reason))

    def zkillban(self, ip_address):
        """Removes a ban.

        ip_address: a string representing the IP address to un-ban

        """
        # logging.debug('')
        return self.send_to_zserv('killban %s' % (ip_address))

    def zmap(self, map_number):
        """Changes the current map.

        map_number: an int representing the number of the map to
                    change to

        """
        # logging.debug('')
        return self.send_to_zserv('map %s' % (map_number))

    def zmaplist(self):
        """Gets the maplist.

        Returns a list of strings representing the names of maps in
        the maplist.  An example of one of these strings is: "map01".

        """
        # logging.debug('')
        return self.send_to_zserv('maplist', 'maplist_command')

    def zplayers(self):
        """Returns a list of players in the server."""
        # logging.debug('')
        return self.send_to_zserv('players', 'players_command')

    def zremovebots(self):
        """Removes all bots."""
        # logging.debug('')
        return self.send_to_zserv('removebots')

    def zresetscores(self):
        """Resets all scores."""
        # logging.debug('')
        return self.send_to_zserv('resetscores')

    def zsay(self, message):
        """Sends a message as ] CONSOLE [.
        
        message: a string representing the message to send.
        
        """
        # logging.debug('')
        return self.send_to_zserv('say %s' % (message))

    def zset(self, variable_name, variable_value):
        """Sets a variable.

        variable_name:  a string representing the name of the variable
                        to set
        variable_value: a string representing the value to set the
                        variable to

        """
        # logging.debug('')
        s = 'set "%s" "%s"' % (variable_name, variable_value)
        return self.send_to_zserv(s)

    def ztoggle(self, boolean_variable):
        """Toggles a boolean variable.

        boolean_variable: a string representing the name of the
                          boolean variable to toggle

        """
        # logging.debug('')
        return self.send_to_zserv('toggle %s' % (boolean_variable))

    def zunset(self, variable_name):
        """Unsets a variable.

        variable_name: a string representing the name of the variable
                       to unset

        """
        # logging.debug('')
        return self.send_to_zserv('unset %s' % (variable_name))

    def zwads(self):
        """Returns a list of the wads in use."""
        # logging.debug('')
        return self.send_to_zserv('wads', 'wads_command')

