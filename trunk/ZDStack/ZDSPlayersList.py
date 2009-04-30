from __future__ import with_statement

import time

from threading import Lock
from collections import deque

from ZDStack import PlayerNotFoundError, get_zdslog
from ZDStack.Utils import requires_instance_lock
from ZDStack.ZDSPlayer import Player

zdslog = get_zdslog()

class PlayersList(object):

    """PlayersList is a threadsafe list of players.

    .. attribute:: zserv
        This PlayersList's containing ZServ instance.

    .. attribute: lock
        A Lock that must be acquired before the internal list of
        players can be modified

    It is possible that many threads will try and modify the players
    list at the same time, with unpredictible results.  PlayersList
    synchronizes access to its internal list of players so that any
    addition or removal of players is done atomically, and so that the
    internal list doesn't change during these operations.

    """

    def __init__(self, zserv):
        """Initializes a PlayersList.
        
        :param zserv: this PlayersList's containing zserv
        :type zserv: ZServ
        
        """
        self.zserv = zserv
        self.lock = Lock()
        self.__players = deque()

    @requires_instance_lock()
    def clear(self):
        """Clears the list of players."""
        self.__players.clear()

    def __iter__(self):
        return self.__players.__iter__()

    def __len__(self):
        return len(self.__players)

    def _player_is_unique(self, player):
        """Returns True if the player is not in the players list."""
        return (player.ip, player.port) not in self.addresses()

    @requires_instance_lock()
    def add(self, player):
        """Adds a player.

        :param player: the player to add
        :type player: Player
        :rtype: boolean
        :returns: True if the player was previously connected this
                  round, i.e., the connection is in fact a
                  re-connection

        """
        zdslog.debug("add(%s)" % (player))
        full_list = []
        name_list = []
        p_full = (player.name, player.ip, player.port)
        p_name = (player.name, player.ip)
        for p in self.__players:
            full_list.append((p.name, p.ip, p.port))
            name_list.append((p.name, p.ip))
        if p_name in name_list:
            ###
            # Player reconnected
            # # Find this player in self.__players and:
            #   set .port to new port
            #   set .disconnected to False
            ###
            zdslog.debug("Player [%s] has reconnected" % (p_name[0]))
            for p in self.__players:
                if (p.name, p.ip) == p_name:
                    p.port = player.port
                    p.disconnected = False
            return True
        else:
            ###
            # Totally new connection
            ###
            zdslog.debug("Found totally new player [%s]" % (p_name[0]))
            self.__players.append(player)
            return False

    @requires_instance_lock()
    def remove(self, player):
        """Disconnects a player.

        :param player: the player to remove
        :type player: Player

        """
        zdslog.debug("remove(%s)" % (player))
        self.set_playing(player, False, acquire_lock=False)
        player.disconnected = True

    @requires_instance_lock()
    def set_playing(self, player, playing):
        """Sets whether or not a player is playing.

        :param player: the player to modify
        :type player: Player
        :param playing: whether or not the player is playing
        :type playing: boolean

        """
        player.playing = playing

    @requires_instance_lock()
    def get(self, name=None, ip_address_and_port=None, sync=True):
        """Returns a Player instance.

        :param name: the name of the player to return
        :type name: string
        :param ip_address_and_port: the IP address and port of the
                                    player to return
        :type ip_address_and_port: tuple, i.e. ('ip_address', port)
        :param sync: a boolean, if True this method performs a sync and
                     reattempts to lookup a player if it is not
                     initially found; True by default
        :rtype: Player

        Either name or ip_address_and_port is optional, but at least
        one must be given.  Note that only giving name can potentially
        return the wrong player, as multiple players can have the same
        name.

        """
        ds = "get(name=%s, ip_address_and_port=%s, sync=%s)"
        zdslog.debug(ds % (name, ip_address_and_port, sync))
        # zdslog.debug('')
        if name and ip_address_and_port:
            ip_address, port = ip_address_and_port
            def find_player():
                for player in self:
                    if player.name == name and \
                       player.ip == ip_address and \
                       player.port == port:
                        return player
        elif name:
            def find_player():
                for player in self:
                    if player.name == name:
                        return player
        elif ip_address_and_port:
            ip_address, port = ip_address_and_port
            def find_player():
                for player in self:
                    if player.ip == ip_address and player.port == port:
                        return player
        else:
            raise TypeError("One of name or ip_address_and_port is required")
        p = None
        p = find_player()
        if p is None and sync:
            ###
            # Didn't find the player, sync & try again.
            ###
            zdslog.debug("Player not found, re-syncing")
            self.sync(acquire_lock=False)
            p = find_player()
        if p:
            return p
        ###
        # Freak out.
        ###
        if sync:
            zdslog.debug("Player still not found, erroring")
        else:
            zdslog.debug("Player not found, erroring")
        raise PlayerNotFoundError(name, ip_address_and_port)

    @requires_instance_lock()
    def sync(self, zplayers=None, sleep=None):
        """Syncs the internal players list with the running zserv.

        :param zplayers: optional, the output from
                         self.zserv.zplayers()
        :type zplayers: a list of dicts
        :param sleep: optional, the amount of time to sleep before
                      manually acquiring the list of players from
                      self.zserv; defaults to None, and is only used
                      when zplayers is None
        :type sleep: int or Decimal or float

        """
        ###
        # When setting a player's name, it's important to use 'set_name', so
        # the alias is saved in the DB.
        ###
        ds = "sync(zplayers=%s)"
        zdslog.debug(ds % (zplayers))
        if zplayers is None:
            if sleep:
                time.sleep(sleep)
            zdslog.debug("Manually populating zplayers")
            zplayers = self.zserv.zplayers()
        pl = [x for x in self if not x.disconnected]
        dpl = [x for x in self if x.disconnected]
        zdslog.debug("Sync: zplayers: (%s)" % (zplayers))
        zdslog.debug("Sync: Players List: (%s)" % (pl))
        zdslog.debug("Sync: Disconnected List: (%s)" % (dpl))
        ###
        # - Check for players to update (reconnected)
        # - Check for players to remove (disconnected)
        # - Check for players to add    (connected)
        ###
        for p in self:
            current_status = 'disconnected'
            current_match = None
            current_port = p.port
            for d in zplayers:
                if not p.ip == d['player_ip'] or \
                   not p.name == d['player_name']:
                    ###
                    # Players do not match.
                    ###
                    continue
                current_match = d
                if p.port == d['player_port']:
                    current_status = 'connected'
                else:
                    current_status = 'reconnected'
            if current_status == 'disconnected':
                p.disconnected = True
            else:
                p.disconnected = False
                if p.number != current_match['player_num']:
                    p.number = current_match['player_num']
                if current_status == 'reconnected':
                    p.port = current_match['player_port']
        for d in zplayers:
            addr = (d['player_ip'], d['player_port'])
            try:
                p = self.get(name=d['player_name'], ip_address_and_port=addr,
                             sync=False, acquire_lock=False)
            except PlayerNotFoundError:
                ###
                # Found a new player!
                ###
                p = Player(self.zserv, d['player_ip'], d['player_port'],
                           d['player_name'] or None,
                           d['player_num'])
                zdslog.debug("Adding new player [%s]" % (p.name))
                self.__players.append(p)
        zdslog.debug("Sync: done")

    def names(self):
        """The names of all this PlayersList's Players.

        :rtype: a list of strings
        :returns: the names of all the players in this PlayersList

        """
        return [x.name for x in self if x.name]

    def addresses(self):
        """The addresses of all this PlayersList's Players.

        :rtype: a list of tuples
        :returns: a list of 2-Tuples (ip, port) for all players.
        
        """
        return [(x.ip, x.port) for x in self]

    @requires_instance_lock()
    def get_first_matching_player(self, possible_player_names):
        """Returns the player whose name matches a list of names.

        :param possible_player_names: the player names to check
        :type possible_player_names: a list of strings
        :rtype: Player
        :returns: the player whose name matches the earliest name in
                  'possible_player_names'

        """
        names = self.names()
        if isinstance(possible_player_names, basestring):
            possible_player_names = [possible_player_names]
        for pn in possible_player_names:
            if pn in names:
                return self.get(name=pn, sync=False, acquire_lock=False)
        zdslog.debug("Names: [%s]" % (names))
        zdslog.debug("PPN: [%s]" % (possible_player_names))

