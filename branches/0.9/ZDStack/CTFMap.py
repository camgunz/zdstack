from ZDStack.TeamMap import TeamMap
from ZDStack.CTFStatKeeper import CTFStatKeeper

class CTFMap(TeamMap, CTFStatKeeper):

    def __init__(self, number, name):
        TeamMap.__init__(self, number, name)
        CTFStatKeeper.__init__(self)

    def initialize(self):
        TeamMap.initialize(self)
        CTFStatKeeper.initialize(self)

    def set_map(self, map):
        pass

    def set_team(self, team):
        pass

    def set_has_flag(self, has_flag):
        pass

