from ZDStack import get_ratio
from ZDStack.TeamPlayer import TeamPlayer
from ZDStack.CTFStatKeeper import CTFStatKeeper

class CTFPlayer(TeamPlayer, CTFStatKeeper):

    def __init__(self, name, zserv, ip=None):
        TeamPlayer.__init__(self, name, zserv, ip)
        CTFStatKeeper.__init__(self)

    def export_summary(self):
        d = self.export()
        s = TeamPlayer.export_summary(self)
        ###
        # self.flag_drops = Listable()
        # self.flag_losses = Listable()
        # self.flag_touches = 0
        # self.flag_returns = 0
        # self.flag_picks = 0
        # self.flag_caps = 0
        ###

