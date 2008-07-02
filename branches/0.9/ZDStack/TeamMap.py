from ZDStack.BaseMap import BaseMap
from ZDStack.TeamStatKeeper import TeamStatKeeper

class TeamMap(BaseMap, TeamStatKeeper):

    def __init__(self, number, name):
        BaseMap.__init__(self, number, name)
        TeamStatKeeper.__init__(self)

