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

    It is possible that many threads will try and modify the players
    list at the same time, with unpredictible results.  PlayersList
    serializes access to its internal list of players so that any
    addition or removal of players is done atomically, and so that the
    internal list doesn't change during these operations.

    """

    ###
    # PlayersList was moved out of ZServ because it had taken on a life
    # of its own.  The code is way clearer with this separated out.
    ###

    def __init__(self, zserv):
        """Initializes a PlayersList.
        
        zserv: the ZServ instance this PlayersList is holding players
               for.
        
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

    def _player_is_unique(self, player):
        """Returns True if the player is not in the players list."""
        return (player.ip, player.port) not in self.addresses()

    @requires_instance_lock()
    def add(self, player):
        """Adds a player.

        player:       a Player instance.

        Returns True if the player was previously connected this round,
        i.e., the connection is in fact a re-connection.

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

        player:       a Player instance.

        """
        zdslog.debug("remove(%s)" % (player))
        self.set_playing(player, False, acquire_lock=False)
        player.disconnected = True

    @requires_instance_lock()
    def set_playing(self, player, playing):
        player.playing = playing

    @requires_instance_lock()
    def get(self, name=None, ip_address_and_port=None, sync=True):
        """Returns a Player instance.

        name:                the name of the player to return.
        sync:                a boolean that, if given, performs a sync
                             and reattempts to lookup a player if it is
                             not initially found.  True by default.
        ip_address_and_port: a 2-Tuple (ip_address, port), both
                             strings.

        Either name or ip_address_and_port is optional, but at least
        one must be given.  Note that only giving name can potentially
        return the wrong player, as multiple players can have the same
        name.

        """
        ds = "get(name=%s, ip_address_and_port=%s)"
        zdslog.debug(ds % (name, ip_address_and_port))
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

        zplayers:     a list of dicts representing zserv's players.
                      If not given, it is acquired from self.zserv.
        sleep:        an int/Decimal/float representing the number of
                      seconds to sleep before manually acquiring the
                      list of players from self.zserv.  Defaults to not
                      sleeping at all, and is only used when zplayers
                      is None.

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
                   not player.name == d['player_name']:
                    ###
                    # Players do not match.
                    ###
                    continue
                current_match = d
                if player.port == d['player_port']:
                    current_status = 'connected'
                else:
                    current_status = 'reconnected'
            if current_status == 'disconnected':
                player.disconnected = True
            else:
                player.disconnected = False
                if player.number != current_match['number']:
                    player.number = current_match['number']
                if current_status == 'reconnected':
                    player.port = current_match['player_port']
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
                           d['player_number'])
                zdslog.debug("Adding new player [%s]" % (p.name))
                self.__players.append(player)
        zdslog.debug("Sync: done")

    def names(self):
        """Returns a list of player names."""
        return [x.name for x in self if x.name]

    def addresses(self):
        """Returns a list of 2-Tuples (ip, port) for all players."""
        return [(x.ip, x.port) for x in self]

    @requires_instance_lock()
    def get_first_matching_player(self, possible_player_names):
        """Returns the player whose name matches a list of names.

        possible_player_names: a list of strings representing player
                               names.

        Given a list of names, get_first_matching_player will return
        a player whose name matches a name in the list.  Each name in
        the list is tested, when a name matches, the matching player
        is returned.

        """
        names = self.names()
        if isinstance(possible_player_names, basestring):
            possible_player_names = [possible_player_names]
        for pn in possible_player_names:
            if pn in names:
                return self.get(name=pn, sync=False, acquire_lock=False)
        zdslog.debug("Names: [%s]" % (names))
        zdslog.debug("PPN: [%s]" % (possible_player_names))

