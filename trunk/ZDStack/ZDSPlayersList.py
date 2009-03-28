from __future__ import with_statement

from threading import Lock
from collections import deque

from ZDStack.ZDSPlayer import Player

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
        return self.__players

    def _player_is_unique(self, player):
        """Returns True if the player is not in the players list."""
        return (player.ip, player.port) not in self.addresses()

    def add(self, player, acquire_lock=True):
        """Adds a player - threadsafe if lock acquired.

        player:       a Player instance.
        acquire_lock: if True, will acquire self.lock before
                      taking any action; True by default.

        """
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
                logging.debug("Player [%s] has reconnected" % (p_name[0]))
                for p in self.__players:
                    if (p.name, p.ip) == p_name:
                        p.port = player.port
                        p.disconnected = False
            else:
                ###
                # Totally new connection
                ###
                logging.debug("Found totally new player [%s]" % (p_name[0]))
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
        def blah():
            player.playing = False
            player.disconnected = True
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def get(self, name=None, ip_address_and_port=None):
        """Returns a Player instance.

        name:                the name of the player to return.
        ip_address_and_port: a 2-Tuple (ip_address, port), both
                             strings.

        Either name or ip_address_and_port is optional, but at least
        one must be given.  Note that only giving name can potentially
        return the wrong player, as multiple players can have the same
        name.

        """
        # logging.debug('')
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
            raise ValueError("One of name or ip_address_and_port is required")
        p = None
        with self.lock:
            p = find_player()
        if p is None:
            ###
            # Didn't find the player, sync & try again.
            ###
            self.sync()
            with self.lock:
                p = find_player()
        if p is None:
            ###
            # Freak out
            ###
            raise PlayerNotFoundError(name, ip_address_and_port)
        return p

    def sync(self, zplayers, acquire_lock=True):
        """Syncs the internal players list with the running zserv.

        zplayers:     a list of dicts representing zserv's players.
        acquire_lock: an optional boolean whether or not to acquire
                      self.lock, True by default.

        """
        ###
        # When setting a player's name, it's important to use 'set_name', so
        # the alias is saved in the DB.
        ###
        def blah():
            players_list = []
            disconnected_players_list = []
            zplayers_list = []
            zplayers_list_plus_numbers = []
            players_list = []
            for x in [x for x in self if x.name]:
                z_full = (x.name, x.ip, x.port)
                players_list.append(z_full)
                if x.disconnected:
                    disconnected_players_list.append(z_full)
            for d in [x for x in zplayers if x['player_name']]:
                z_full = (d['player_name'], d['player_ip'], d['player_port'])
                z_full_plus_number = (d['player_num'],) + z_full
                zplayers_list.append(z_full)
                zplayers_list_plus_numbers.append(z_full_plus_number)
            for z_full in zplayers_list:
                if z_full not in players_list or \
                   z_full in disconnected_players_list:
                    ###
                    # found a missing or reconnected player
                    ###
                    player = Player(self.zserv, z_full[1], z_full[2], z_full[0])
                    self.add(player, acquire_lock=not acquire_lock)
                    logging.debug("Added new player [%s]" % (player.name))
            for p_full in players_list:
                if p_full not in zplayers_list:
                    ###
                    # Found a ghost player...?
                    ###
                    player = self.get(name=p_full[0],
                                      ip_address_and_port=p_full[1:])
                    logging.debug("Removed player [%s]" % (p_full[0]))
                    self.remove(player, acquire_lock=not acquire_lock)
            for z_full_num in zplayers_list_plus_numbers:
                for p in self:
                    if (p.name, p.ip, p.port) == z_full_num[1:]:
                        if p.number != z_full_num[0]:
                            if p.name.endswith('s'):
                                es = "Set %s' number to %s"
                            else:
                                es = "Set %s's number to %s"
                            logging.debug(es % (p.name, z_full_num[0]))
                            p.number = z_full_num[0]
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

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
                    return self.get(name=name)

