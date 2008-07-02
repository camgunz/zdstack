from ZDStack.BasePlayer import BasePlayer
from ZDStack.TeamStatKeeper import TeamStatKeeper

class TeamPlayer(BasePlayer, TeamStatKeeper):

    def __init__(self, name, zserv, ip=None):
        BasePlayer.__init__(self, name, zserv, ip)
        TeamStatKeeper.__init__(self)
        self.color = None

    def exportables(self):
        out = []
        for x in BasePlayer.exportables(self):
            if x[0] != 'team' and \
              (('team' in self and x[1] != self.team) or \
               ('team' not in self)):
                out.append(x)
        return out

