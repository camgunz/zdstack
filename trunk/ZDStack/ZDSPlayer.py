from ZDStack import get_zdslog
from ZDStack.Utils import homogenize, parse_player_name, html_escape
from ZDStack.ZDSDatabase import get_alias, get_team_color

zdslog = get_zdslog()

class Player(object):

    """A Player represents a player who's connected to a server.

    .. attribute:: zserv
        This player's containing ZServ instance

    .. attribute:: ip
        A string represenging this player's IP address

    .. attribute:: port
        An int representing the port this player is connecting from

    .. attribute:: number
        An int representing this player's position in the ZServ's list
        of players

    .. attribute:: name
        A string representing this player's complete name

    .. attribute:: tag
        A string representing this player's tag, can be None

    .. attribute:: player_name
        A string representing this player's name without the tag, can
        be the same as 'name'

    .. attribute:: playing
        A boolean, whether or not the player is currently playing

    .. attribute:: disconnected
        A boolean, whether or not the player is currently disconnected

    """

    def __init__(self, zserv, ip_address, port, name=None, number=None):
        """Initializes a BasePlayer.

        :param zserv: This player's containing ZServ instance
        :type zserv: ZServ
        :param ip_address: This player's IP address
        :type ip_address: string
        :param port: The port this player is connecting from
        :type port: int
        :param name: This player's name
        :type name: string
        :param number: The player's position in its ZServ's list of
                       players
        :type number: int

        """
        zdslog.debug('name: [%s]' % (name))
        self.zserv = zserv
        self.ip = ip_address
        self.port = int(port)
        self.number = number
        self.name = ''
        self.tag = None
        self.player_name = ''
        if name:
            self.set_name(name)
        self.color = None
        self.playing = False
        self.disconnected = False

    def set_name(self, name):
        """Sets this player's name.

        :param name: the new name of this player
        :type name: string

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
        """Gets this player's Alias model.
        
        :param session: a Session instance, if none is given, the global
                        session will be used
        :type session: Session
        :rtype: Alias
        
        """
        zdslog.debug("Getting Alias for %s, %s" % (self.name, self.ip))
        return get_alias(name=self.name, ip_address=self.ip,
                         round=self.zserv.get_round(session=session),
                         session=session)

    def get_team_color(self, session=None):
        """Gets this player's TeamColor model.

        :param session: a Session instance, if none is given, the global
                        session will be used
        :type session: Session
        :rtype: TeamColor
        
        """
        zdslog.debug("Getting TeamColor for %s, %s" % (self.name, self.ip))
        return get_team_color(self.color, session=session)

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
            return "Player(%s, %s)" % (self.ip, self.port)

