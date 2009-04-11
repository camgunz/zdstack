import logging

from ZDStack.Utils import homogenize, parse_player_name, html_escape

from ZDStack.ZDSDatabase import get_alias

class Player(object):

    def __init__(self, zserv, ip_address, port, name=None, number=None):
        """Initializes a BasePlayer.

        zserv:      a ZServ instance.
        ip_address: a string representing the IP address of the player
        port:       a string representing the port of the player
        name:       optional, a string representing the name of the
                    player
        number:     optional, a string representing the number of the
                    player

        """
        logging.debug('name: [%s]' % (name))
        self.zserv = zserv
        self.ip = ip_address
        self.port = port
        self.number = number
        self.name = ''
        self.tag = None
        self.player_name = ''
        self.alias = None
        if name:
            self.set_name(name)
        self.playing = False
        self.disconnected = False

    def set_name(self, name):
        """Sets this player's name.

        name: a string representing the new name of this player

        """
        if self.name == name or not name:
            ###
            # Why go through all this work if name is None... or there's been
            # no change?
            ###
            return
        self.name = name
        self.tag, self.player_name = parse_player_name(self.name)
        self.alias = get_alias(name=self.name, ip_address=self.ip)
        # if self.alias not in self.zserv.round.players:
        #     self.zserv.round.players.append(self.alias)

    def __ne__(self, x):
        try:
            return not (self.port == x.port and self.ip == x.ip)
        except NameError:
            return True

    def __eq__(self, x):
        try:
            return (self.port == x.port and self.ip == x.ip)
        except NameError:
            return False

    def __str__(self):
        if self.name:
            return "<Player [%s]>" % (self.name)
        else:
            return "<Player [%s:%s]>" % (self.ip, self.port)

    def __repr__(self):
        if self.name:
            return "Player(%s)" % (self.name)
        else:
            return "Player(%s, %s)" % (self.ip_address, self.port)

