from ZDSModels import Alias

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
        self.homogenized_name = ''
        self.escaped_name = ''
        self.escaped_homogenized_name = ''
        self.encoded_name = ''
        self.homogenized_player_name = ''
        self.escaped_player_name = ''
        self.escaped_homogenized_player_name = ''
        if name:
            self.set_name(name)
        self.playing = False
        self.has_played_this_round = False
        self.disconnected = False
        ###
        # TODO:
        #   - Add latency/packet-loss tracking
        ###

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
        self.homogenized_name = homogenize(self.name)
        self.escaped_name = html_escape(self.name)
        self.escaped_homogenized_name = html_escape(self.homogenized_name)
        self.encoded_name = b64encode(self.name)
        self.homogenized_player_name = homogenize(self.player_name)
        self.escaped_player_name = html_escape(self.player_name)
        self.escaped_homogenized_player_name = \
                                    html_escape(self.homogenized_player_name)
        if self.tag is None:
            self.homogenized_tag = None
            self.escaped_tag = None
            self.escaped_homogenized_tag = None
        else:
            self.homogenized_tag = homogenize(self.tag)
            self.escaped_tag = html_escape(self.tag)
            self.escaped_homogenized_tag = html_escape(self.homogenized_tag)
        ###
        # We want to create an Alias mapping this name to this IP address.  If
        # no such Alias exists, create one.
        ###
        self.zserv.session.add(Alias(name=self.name, ip_address=self.ip))

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
            return "<Player [%s:%s]>" % (self.ip_address, self.port)

    def __repr__(self):
        if self.name:
            return "Player(%s)" % (self.name)
        else:
            return "Player(%s, %s)" % (self.ip_address, self.port)

