import logging
import tempfile

from ZDStack import set_debugging
from ZDStack.BaseMap import BaseMap
from ZDStack.BaseStats import BaseStats
from ZDStack.BasePlayer import BasePlayer
from ZDStack.FakeLogFile import FakeLogFile
from ZDStack.Dictable import Dictable
from ZDStack.LogParser import GeneralLogParser
from ZDStack.LogListener import GeneralLogListener
from ZDStack.GeneralZServStatsMixin import GeneralZServStatsMixin

from pyfileutils import get_temp_dir

set_debugging(True)

class FakeZServ(GeneralZServStatsMixin):

    """BaseFakeZServ is a FakeZServ for client log parsing."""

    # There are probably a lot of race conditions here...
    # TODO: add locks, specifically in RPC-accessible methods and
    #       around the data structures they use.

    def __init__(self, memory_slots=10, player_class=BasePlayer,
                                        map_class=BaseMap,
                                        stats_class=BaseStats,
                                        log_type='server'):
        """Initializes a BaseZServ instance.

        memory_slots: an int representing the # of maps to remember
        player_class: the player class to use
        map_class:    the map class to use
        stats_class:  the stats class to use
        log_type:     specifies which type of log to parse, valid
                      options are "server" and "client"

        """
        self.name = 'fakezserv'
        self.type = 'base'
        self.pre_spawn_funcs = []
        self.post_spawn_funcs = []
        self.extra_exportables_funcs = []
        load_plugins = False
        self.config = {}
        GeneralZServStatsMixin.__init__(self, memory_slots, player_class,
                                              map_class, stats_class,
                                              load_plugins, log_type)
        self.start_collecting_general_stats()
        self.config = {}
        self.homedir = get_temp_dir(dir=tempfile.gettempdir())

    def start_collecting_general_stats(self):
        """Starts collecting statistics."""
        # logging.debug('')
        self.initialize_general_stats()
        general_log_parser = \
            GeneralLogParser(log_type=self.log_type, fake=True)
        self.general_log = FakeLogFile('general', general_log_parser, self)
        self.general_log_listener = GeneralLogListener(self)
        self.general_log.listeners = [self.general_log_listener]
        for listener in self.general_log.listeners:
            logging.debug("Starting %s" % (listener))
            listener.start()
        # self.set_general_log_filename()
        # self.general_log.start()

    def parse_log(self, filepath):
        self.general_log.parse_log(filepath)

    def get_general_log_filename(self, roll=False):
        return "NOTALOGFILE"

    def set_general_log_filename(self, roll=False):
        pass

    def __str__(self):
        return "<FakeZServ [%s]>" % (self.name)

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
            self.add_player(name)
            return self.get_player(name)
            # raise ValueError("Player [%s] not found" % (name))
        else:
            raise ValueError("Address [%s:%s] not found" % ip_address_and_port)

    def add_player(self, player_name):
        """Adds a player to self.players

        player_name: a string representing the nameof the new player.

        """
        logging.debug("Adding player: [%s]" % (player_name))
        player = self.player_class(self, None, None, name=player_name,
                                   log_ip=False)
        if player_name in [p.name for p in self.players]:
            ###
            # A duplicate player has connected
            if not hasattr(player, 'instances'):
                player.instances = 1
            player.instances += 1
            self.players.append(player)
        elif player_name in [p.name for p in self.disconnected_players]:
            ###
            # A player has reconnected
            self.disconnected_players = \
                [x for x in self.disconnected_players is x.name != player_name]
            player.disconnected = False
            player.instances += 1
        else:
            ###
            # A player is connecting for the first time
            self.players.append(player)
        self.update_player_numbers_and_ips()

    def remove_player(self, player_name):
        """Disconnects a player.

        player_name: the name of the player to disconnect
        
        """
        # logging.debug('')
        player = self.get_player(name=player_name)
        player.disconnected = True
        player.playing = False
        if player in self.players:
            if player not in self.disconnected_players:
                if not hasattr(player, 'instances'):
                    player.instances = 1
                player.instances -= 1
                if player.instances <= 0:
                    self.disconnected_players.append(player)

    def export(self):
        """Returns a dict of ZServ configuration information."""
        logging.debug('')
        d = {'stats_should_go_here': 'whoo stats!'}
        for func, args, kwargs in self.extra_exportables_funcs:
            d = func(*([d] + args), **kwargs)
        return Dictable(d).export()

    ###
    # Try to get along without this stuff for now
    ###
    def get_player_ip_address(self, player_name): pass
    def get_player_number(self, player_name): pass
    def update_player_numbers_and_ips(self): pass
    def send_to_zserv(self, message, event_response_type): pass
    def zaddban(self, ip_address, reason='rofl'): pass
    def zaddtimeban(self, duration, ip_address, reason='rofl'): pass
    def zaddbot(self, bot_name): pass
    def zaddmap(self,map_number): pass
    def zclearmaplist(self): pass
    def zget(self, variable_name): pass
    def zkick(self, player_number, reason='rofl'): pass
    def zkillban(self, ip_address): pass
    def zmap(self, map_number): pass
    def zmaplist(self): pass
    def zplayers(self): pass
    def zremovebots(self):pass
    def zresetscores(self): pass
    def zsay(self): pass
    def zset(self, variable_name, variable_value): pass
    def ztoggle(self, boolean_variable): pass
    def zunset(self, variable_name): pass
    def zwads(self): pass

