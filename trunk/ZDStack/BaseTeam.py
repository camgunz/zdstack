from ZDStack import debug
from ZDStack.TeamStatKeeper import TeamStatKeeper

class BaseTeam(TeamStatKeeper):

    def __init__(self, color):
        TeamStatKeeper.__init__(self)
        self.name = color
        self.color = color

    def set_team(self, team):
        pass

    def set_map(self, map):
        debug()
        self.map = map
        self.stat_container = map

