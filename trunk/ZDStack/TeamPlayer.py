from ZDStack.BasePlayer import BasePlayer
from ZDStack.TeamStatKeeper import TeamStatKeeper

class TeamPlayer(BasePlayer, TeamStatKeeper):

    """TeamPlayer represents a Player in a team game."""

    def __init__(self, zserv, ip_address, port, name=None, log_ip=True):
        """Initializes a TeamPlayer.

        zserv:      a ZServ instance
        ip_address: a string representing the IP address of the player
        port:       a string representing the port of the player
        name:       optional, a string representing the name of the
                    player
        log_ip:     if True, will log this Player's IP.  True by
                    default.

        """
        BasePlayer.__init__(self, zserv, ip_address, port, name, log_ip)
        TeamStatKeeper.__init__(self)
        self.color = None

    def initialize(self):
        """Initializes TeamPlayer's stats."""
        BasePlayer.initialize(self)
        TeamStatKeeper.initialize(self)

    def exportables(self):
        """Returns a list of strings representing exportable attributes."""
        out = []
        for x in BasePlayer.exportables(self):
            if x[0] != 'team' and \
              (('team' in self and x[1] != self.team) or \
               ('team' not in self)):
                out.append(x)
        return out

