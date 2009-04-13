from __future__ import with_statement

from threading import Lock
from collections import deque

from ZDStack import PlayerNotFoundError, get_zdslog
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

    def clear(self):
        """Clears the list of players."""
        with self.lock:
            self.__players.clear()

    def __iter__(self):
        return self.__players.__iter__()

    def _player_is_unique(self, player):
        """Returns True if the player is not in the players list."""
        return (player.ip, player.port) not in self.addresses()

    def add(self, player, acquire_lock=True):
        """Adds a player - threadsafe if lock acquired.

        player:       a Player instance.
        acquire_lock: if True, will acquire self.lock before
                      taking any action; True by default.

        """
        zdslog.debug("add(%s, acquire_lock=%s" % (player, acquire_lock))
        def blah():
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
            else:
                ###
                # Totally new connection
                ###
                zdslog.debug("Found totally new player [%s]" % (p_name[0]))
                self.__players.append(player)
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def remove(self, player, acquire_lock=True):
        """Disconnects a player - threadsafe if lock acquired.

        player:       a Player instance.
        acquire_lock: if True, will acquire self.lock before
                      taking any action; True by default.

        """
        zdslog.debug("remove(%s, acquire_lock=%s" % (player, acquire_lock))
        def blah():
            player.playing = False
            player.disconnected = True
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def get(self, name=None, ip_address_and_port=None, sync=True,
                  acquire_lock=True):
        """Returns a Player instance.

        name:                the name of the player to return.
        sync:                a boolean that, if given, performs a sync
                             and reattempts to lookup a player if it is
                             not initially found.  True by default.
        ip_address_and_port: a 2-Tuple (ip_address, port), both
                             strings.
        acquire_lock:        a boolean that, if given, acquires the
                             players lock before looking a player up.
                             True by default.

        Either name or ip_address_and_port is optional, but at least
        one must be given.  Note that only giving name can potentially
        return the wrong player, as multiple players can have the same
        name.

        """
        zdslog.debug("get(name=%s, ip_address_and_port=%s, acquire_lock=%s" % (name, ip_address_and_port, acquire_lock))
        # zdslog.debug('')
        if name and ip_address_and_port:
            ip_address, port = ip_address_and_port
            def _find_player():
                for player in self:
                    if player.name == name and \
                       player.ip == ip_address and \
                       player.port == port:
                        return player
        elif name:
            def _find_player():
                for player in self:
                    if player.name == name:
                        return player
        elif ip_address_and_port:
            ip_address, port = ip_address_and_port
            def _find_player():
                for player in self:
                    if player.ip == ip_address and player.port == port:
                        return player
        else:
            raise ValueError("One of name or ip_address_and_port is required")
        def find_player(acquire_lock=True):
            if acquire_lock:
                with self.lock:
                    return _find_player()
            else:
                return _find_player()
        p = None
        p = find_player(acquire_lock=acquire_lock)
        if p is None and sync:
            ###
            # Didn't find the player, sync & try again.
            ###
            self.sync(acquire_lock=acquire_lock)
            p = find_player(acquire_lock=acquire_lock)
        if p is None:
            ###
            # Freak out
            ###
            raise PlayerNotFoundError(name, ip_address_and_port)
        return p

    def sync(self, zplayers=None, acquire_lock=True):
        """Syncs the internal players list with the running zserv.

        zplayers:     a list of dicts representing zserv's players.
                      If not given, it is acquired from self.zserv.
        acquire_lock: an optional boolean whether or not to acquire
                      self.lock, True by default.

        """
        ###
        # When setting a player's name, it's important to use 'set_name', so
        # the alias is saved in the DB.
        ###
        zdslog.debug("sync(zplayers=%s, acquire_lock=%s" % (zplayers, acquire_lock))
        def blah():
            players_list = list()
            disconnected_players_list = list()
            zplayers_list = list()
            zplayers_list_plus_numbers = list()
            players_list = []
            for x in [x for x in self if x.name]:
                z_full = (x.name, x.ip, x.port)
                players_list.append(z_full)
                if x.disconnected:
                    disconnected_players_list.append(z_full)
            # for d in [x for x in zplayers if x['player_name']]:
            for d in zplayers:
                z_full = (d['player_name'], d['player_ip'], d['player_port'])
                z_full_plus_number = (d['player_num'],) + z_full
                zplayers_list.append(z_full)
                zplayers_list_plus_numbers.append(z_full_plus_number)
            zdslog.debug("Sync: Players List: (%s)" % (players_list))
            zdslog.debug("Sync: Disconnected List: (%s)" % (disconnected_players_list))
            zdslog.debug("Sync: ZPlayers List: (%s)" % (zplayers_list))
            zdslog.debug("Checking for players to add")
            for z_full in zplayers_list:
                if z_full not in players_list or \
                   z_full in disconnected_players_list:
                    ###
                    # found a missing or reconnected player
                    ###
                    player = Player(self.zserv, z_full[1], z_full[2], z_full[0])
                    zdslog.debug("Adding new player [%s]" % (player.name))
                    self.add(player, acquire_lock=False)
                    zdslog.debug("Added new player [%s]" % (player.name))
            zdslog.debug("Checking for players to remove")
            for p_full in players_list:
                if p_full not in zplayers_list:
                    ###
                    # Found a ghost player...?
                    ###
                    player = self.get(name=p_full[0],
                                      ip_address_and_port=p_full[1:],
                                      acquire_lock=False)
                    zdslog.debug("Removed player [%s]" % (p_full[0]))
                    self.remove(player, acquire_lock=False)
            zdslog.debug("Checking for misaligned numbers")
            for z_full_num in zplayers_list_plus_numbers:
                for p in self:
                    zdslog.debug("Checking %s" % (p))
                    if p.name.endswith('s'):
                        ps = "%s'"
                    else:
                        ps = "%s's"
                    x = (p.name, p.ip, p.port)
                    if x == z_full_num[1:]:
                        if p.number != z_full_num[0]:
                            es = "Set %s number to %%s" % (ps)
                            es = es % (p.name, z_full_num[0])
                            p.number = z_full_num[0]
                        else:
                            es = "%s number was aligned properly" % (ps)
                            es = es % (p.name)
                    else:
                        es = "%s and %s don't match" % (str(x),
                                                        str(z_full_num[1:]))
                    zdslog.debug(es)
        if acquire_lock:
            with self.lock:
                if zplayers is None:
                    zdslog.debug("Manually populating zplayers")
                    zplayers = self.zserv.zplayers()
                zdslog.debug("Sync: zplayers: (%s)" % (zplayers))
                blah()
        else:
            if zplayers is None:
                zdslog.debug("Manually populating zplayers")
                zplayers = self.zserv.zplayers()
            zdslog.debug("Sync: zplayers: (%s)" % (zplayers))
            blah()
        zdslog.debug("Sync: done")

    def names(self):
        """Returns a list of player names."""
        return [x.name for x in self if x.name]

    def addresses(self):
        """Returns a list of 2-Tuples (ip, port) for all players."""
        return [(x.ip, x.port) for x in self]

    def get_first_matching_player(self, possible_player_names):
        """Returns the player whose name matches a list of names.

        possible_player_names: a list of strings representing player
                               names.

        Given a list of names, get_first_matching_player will return
        a player whose name matches a name in the list.  Each name in
        the list is tested, when a name matches, the matching player
        is returned.

        """
        with self.lock:
            ###
            # Don't want the lists changing on us in the middle of matching
            # players to names.
            ###
            names = self.names()
            for pn in possible_player_names:
                if pn in names:
                    return self.get(name=name, sync=False, acquire_lock=False)

