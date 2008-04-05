from ZDStack.BaseStatKeeper import BaseStatKeeper

class Team(BaseStatKeeper):

    def __init__(self, color):
        self.color = color
        self.map = None
        BaseStatKeeper.__init__(self, self.map)

    def set_map(self, new_map):
        self.map = new_map
        self.stat_container = self.map

