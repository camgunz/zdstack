from ZDStack.BasePlayer import BasePlayer
from ZDStack.TeamStatKeeper import TeamStatKeeper

class TeamPlayer(BasePlayer, TeamStatKeeper):

    """TeamPlayer represents a Player in a team game."""

    def __init__(self, name, zserv, ip=None):
        """Initializes a TeamPlayer.

        name:  a string representing the name of the player
        zserv: a ZServ instance
        ip:    optional, a string representing the IP address of the
               player.

        """
        BasePlayer.__init__(self, name, zserv, ip)
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

