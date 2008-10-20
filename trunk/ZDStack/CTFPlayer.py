from ZDStack.Utils import get_ratio
from ZDStack.TeamPlayer import TeamPlayer
from ZDStack.CTFStatKeeper import CTFStatKeeper

class CTFPlayer(TeamPlayer, CTFStatKeeper):

    """CTFPlayer represents a Capture the Flag player."""

    def __init__(self, zserv, ip_address, port, name=None, log_ip=True):
        """Initializes a CTFPlayer instance.

        zserv:      a ZServ instance
        ip_address: a string representing the IP address of the player
        port:       a string representing the port of the player
        name:       optional, a string representing the name of the
                    player
        log_ip:     if True, will log this Player's IP.  True by
                    default.

        """
        TeamPlayer.__init__(self, zserv, ip_address, port, name, log_ip)
        CTFStatKeeper.__init__(self)

    def initialize(self):
        """Initializes this CTFPlayer's stats."""
        TeamPlayer.initialize(self)
        CTFStatKeeper.initialize(self)

    def export_summary(self):
        """Exports a summary of this CTFPlayer's stats."""
        d = self.export()
        s = TeamPlayer.export_summary(self)
        self.flag_touches = 0
        self.flag_returns = 0
        self.flag_picks = 0
        self.flag_caps = 0

