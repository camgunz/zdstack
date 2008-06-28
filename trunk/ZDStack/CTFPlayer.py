from ZDStack.Utils import get_ratio
from ZDStack.TeamPlayer import TeamPlayer
from ZDStack.CTFStatKeeper import CTFStatKeeper

class CTFPlayer(TeamPlayer, CTFStatKeeper):

    """CTFPlayer represents a Capture the Flag player."""

    def __init__(self, name, zserv, ip=None):
        """Initializes a CTFPlayer instance.

        name:  a string representing the player's name
        zserv: a ZServ instance
        ip:    optional, a string representing the player's IP address

        """
        TeamPlayer.__init__(self, name, zserv, ip)
        CTFStatKeeper.__init__(self)

    def initialize(self):
        """Initializes this CTFPlayer's stats."""
        TeamPlayer.initialize(self)
        CTFStatKeeper.initialize(self)

    def export_summary(self):
        """Exports a summary of this CTFPlayer's stats."""
        d = self.export()
        s = TeamPlayer.export_summary(self)
        self.flag_drops = Listable()
        self.flag_losses = Listable()
        self.flag_touches = 0
        self.flag_returns = 0
        self.flag_picks = 0
        self.flag_caps = 0

