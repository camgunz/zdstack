from ZDStack import get_zdslog
from ZDStack.Utils import homogenize, parse_player_name, html_escape
from ZDStack.ZDSDatabase import get_alias

zdslog = get_zdslog()

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
        zdslog.debug('name: [%s]' % (name))
        self.zserv = zserv
        self.ip = ip_address
        self.port = port
        self.number = number
        self.name = ''
        self.tag = None
        self.player_name = ''
        if name:
            self.set_name(name)
        self.playing = False
        self.disconnected = False

    def set_name(self, name):
        """Sets this player's name.

        name: a string representing the new name of this player

        """
        zdslog.debug("setting name to [%s]" % (name))
        if self.name == name or not name:
            ###
            # Why go through all this work if name is None... or there's been
            # no change?
            ###
            return
        self.name = name
        self.tag, self.player_name = parse_player_name(self.name)

    def get_alias(self, session=None):
        """Returns an alias representing this player.
        
        session: a session instance, if none is given, the global
                 session will be used.
        
        """
        zdslog.debug("Getting Alias for %s, %s" % (self.name, self.ip))
        return get_alias(name=self.name, ip_address=self.ip,
                         round=self.zserv.round, session=session)

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

