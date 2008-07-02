from ZDStack.TeamPlayer import TeamPlayer
from ZDStack.CTFStatKeeper import CTFStatKeeper

class CTFPlayer(TeamPlayer, CTFStatKeeper):

    def __init__(self, name, zserv, ip=None):
        TeamPlayer.__init__(self, name, zserv, ip)
        CTFStatKeeper.__init__(self)

