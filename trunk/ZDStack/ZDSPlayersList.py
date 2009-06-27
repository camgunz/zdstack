from __future__ import with_statement

import time

from threading import Lock
from collections import deque

from ZDStack import PlayerNotFoundError, get_zdslog
from ZDStack.ZServ import TEAM_MODES
from ZDStack.Utils import requires_instance_lock
from ZDStack.ZDSPlayer import Player
from ZDStack.ZDSModels import Alias
from ZDStack.ZDSDatabase import global_session

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

    @requires_instance_lock()
    def get(self, name=None, ip_address_and_port=None, sync=True):
        """Returns an Alias instance.

        :param name: the name of the player to return
        :type name: string
        :param ip_address_and_port: the IP address and port of the
                                    player to return
        :type ip_address_and_port: tuple, i.e. ('ip_address', port)
        :param sync: a boolean, if True this method performs a sync and
                     reattempts to lookup a player if it is not
                     initially found; True by default
        :rtype: Alias

        Either name or ip_address_and_port is optional, but at least
        one must be given.  Note that only giving name can potentially
        return the wrong player, as multiple players can have the same
        name.

        """
        ds = "get(name=%s, ip_address_and_port=%s, sync=%s)"
        zdslog.debug(ds % (name, ip_address_and_port, sync))
        # zdslog.debug('')
        if ip_address_and_port:
            ip_address, port = (ip_address_and_port[0],
                                int(ip_address_and_port[1]))
            if name:
                def find_player():
                    for player in self:
                        if player.name == name and \
                           player.ip == ip_address and \
                           player.port == port:
                            return player
            else:
                def find_player():
                    for player in self:
                        if player.ip == ip_address and player.port == port:
                            return player
        elif name:
            def find_player():
                for player in self:
                    if player.name == name:
                        return player
        else:
            raise TypeError("One of name or ip_address_and_port is required")
        p = None
        p = find_player()
        if p is None and sync:
            ###
            # Didn't find the player, sync & try again.
            ###
            zdslog.debug("Alias not found, re-syncing")
            self.sync(acquire_lock=False, check_bans=True)
            p = find_player()
        if p:
            return p
        ###
        # Freak out.
        ###
        if sync:
            zdslog.debug("Alias still not found, erroring")
        else:
            zdslog.debug("Alias not found, erroring")
        raise PlayerNotFoundError(name, ip_address_and_port)

    @requires_instance_lock()
    def sync(self, zplayers=None, sleep=None, check_bans=False):
        """Syncs the internal players list with the running zserv.

        :param zplayers: optional, the output from
                         self.zserv.zplayers()
        :type zplayers: a list of dicts
        :param sleep: optional, the amount of time to sleep before
                      manually acquiring the list of players from
                      self.zserv; defaults to None, and is only used
                      when zplayers is None
        :type sleep: int or Decimal or float
        :param check_bans: whether or not to check the sync'd list of
                           players for banned players, and kick them
        :type check_bans: boolean

        """
        ds = "sync(zplayers=%s)"
        zdslog.debug(ds % (zplayers))
        if zplayers is None:
            if sleep:
                time.sleep(sleep)
            zdslog.debug("Manually populating zplayers")
            zplayers = self.zserv.zplayers()
        for d in zplayers:
            d['player_port'] = int(d['player_port'])
            d['player_num'] = int(d['player_num'])
        pl = [x for x in self if not x.disconnected]
        dpl = [x for x in self if x.disconnected]
        zdslog.debug("Sync: zplayers: (%s)" % (zplayers))
        zdslog.debug("Sync: Players List: (%s)" % (pl))
        zdslog.debug("Sync: Disconnected List: (%s)" % (dpl))
        ###
        # - Check for players to update (reconnected)
        # - Check for players to remove (disconnected)
        # - Check for players to add    (new)
        ###
        zdslog.debug("Updating player state")
        for p in self:
            zdslog.debug("Matching up: %s - %s:%s" % (p.name, p.ip, p.port))
            ###
            # 'connected': name, IP and port all match
            # 'reconnected': name and IP match, port does not
            # 'disconnected': not found in zplayers
            ###
            match = None
            for d in zplayers:
                if p.name == d['player_name'] and p.ip == d['player_ip']:
                    ds = "%s - %s:%s matches %s -%s:%s"
                    zdslog.debug(ds % (d['player_name'], d['player_ip'],
                                       d['player_port'], p.name, p.ip, p.port))
                    match = d
                    if d['player_port'] == p.port:
                        break
                else:
                    ds = "%s - %s:%s does not match %s -%s:%s"
                    zdslog.debug(ds % (d['player_name'], d['player_ip'],
                                       d['player_port'], p.name, p.ip, p.port))
            if match:
                zdslog.debug("Updating %s" % (p))
                p.port = match['player_port']
                p.number = match['player_num']
                p.zserv = self.zserv
                p.disconnected = False
                if not hasattr(p, 'playing'):
                    p.playing = False
            else:
                zdslog.debug("Disconnecting %s" % (p))
                p.disconnected = True
        zdslog.debug("Checking for players to add")
        for d in zplayers:
            d['player_port'] = d['player_port']
            if not d['player_name']:
                ###
                # Skip players with blank names, this is just trouble.
                ###
                continue
            zdslog.debug("Checking %s - %s:%s" % (d['player_name'],
                                                  d['player_ip'],
                                                  d['player_port']))
            addr = (d['player_ip'], d['player_port'])
            try:
                p = self.get(name=d['player_name'], ip_address_and_port=addr,
                             sync=False, acquire_lock=False)
            except PlayerNotFoundError:
                ###
                # Found a new player!
                ###
                ###
                # Try and look them up first:
                ###
                zdslog.debug("Found a new player!")
                with global_session() as session:
                    q = session.query(Alias)
                    q = q.filter_by(name=d['player_name'],
                                    ip_address=d['player_ip'])
                    p = q.first()
                    if not p:
                        if not d['player_ip']:
                            es = "Somehow a players command did not return "
                            es += "an IP address to us"
                            raise Exception(es)
                        p = Alias()
                        p.ip_address = d['player_ip']
                        p.port = d['player_port']
                        p.name = d['player_name']
                        session.add(p)
                p.zserv = self.zserv
                p.number = d['player_num']
                p.disconnected = False
                p.playing = False
                zdslog.debug("Adding new player [%s]" % (p.name))
                self.__players.append(p)
        zdslog.debug("Players list: %s" % (self.__players))
        zdslog.debug("Disconnected list: %s" % ([x for x in self if x.disconnected]))
        if self.zserv.game_mode in TEAM_MODES:
            zdslog.debug("Updating player teams")
            for player in [x for x in self if not x.disconnected]:
                for d in self.zserv.zplayerinfo(player.number):
                    if d['playerinfo_attribute'] == 'Color':
                        team_number = d['playerinfo_value']
                        team_color = NUMBERS_TO_COLORS[team_number]
                        if player.color != team_color:
                            ds = "Updating color for %s from %s to %s"
                            t = (player.name, player.color, team_color)
                            zdslog.debug(ds % t)
                        player.color = team_color
        if check_bans:
            self.check_bans(acquire_lock=False)
        else:
            zdslog.debug('Skipping ban check')
        zdslog.debug("Sync: done")

    @requires_instance_lock()
    def check_bans(self):
        """Kicks banned players."""
        zdslog.debug('Checking bans')
        t_string = "You have been banned for the following reason: %s"
        while 1:
            for p in self.__players:
                zdslog.debug('Checking player %s' % (p))
                if p.disconnected:
                    zdslog.debug('%s has disconnected' % (p))
                elif not p.ip:
                    es = "There should never be a player without an IP "
                    es += "address: [%s]."
                    raise Exception(es % (p))
                else:
                    zdslog.debug('%s is not disconnected' % (p))
                    reason = self.zserv.access_list.search_bans(p.ip)
                    if reason:
                        ds = '%s is banned for the following reason: %s'
                        zdslog.debug(ds % (p, reason))
                        if isinstance(reason, basestring) and reason:
                            reason = t_string % (reason)
                        else:
                            reason = 'Banned'
                        zdslog.debug('Kicking %s' % (p))
                        self.zserv.zkick(p.number, reason)
                        self.sync(acquire_lock=False, check_bans=False)
                        break
                    else:
                        zdslog.debug('No ban found for %s@%s' % (p.name, p.ip))
            else:
                zdslog.debug('No bans found')
                break

    @requires_instance_lock()
    def get_first_matching_player(self, possible_player_names):
        """Returns the player whose name matches a list of names.

        :param possible_player_names: the player names to check
        :type possible_player_names: a list of strings
        :rtype: Player
        :returns: the player whose name matches the earliest name in
                  'possible_player_names'

        """
        names = [x.name for x in self]
        if isinstance(possible_player_names, basestring):
            possible_player_names = [possible_player_names]
        for pn in possible_player_names:
            if pn in names:
                return self.get(name=pn, sync=False, acquire_lock=False)
        ###
        # Here we sync, and try again.
        ###
        self.sync(acquire_lock=False, check_bans=True)
        for pn in possible_player_names:
            if pn in names:
                return self.get(name=pn, sync=False, acquire_lock=False)
        ###
        # Otherwise, debug some stuff.
        ###
        zdslog.debug("Names: [%s]" % (names))
        zdslog.debug("PPN: [%s]" % (possible_player_names))

