from ZDStack.BaseStatKeeper import BaseStatKeeper

class Team(BaseStatKeeper):

    def __init__(self, color):
        self.color = color
        self.map = None
        BaseStatKeeper.__init__(self, self.map)

    def exportables(self):
        exportables = BaseStatKeeper.exportables(self)
        return [x for x in exportables if x[1] != self.map]

    def set_map(self, new_map):
        self.map = new_map
        self.stat_container = self.map
        self.map_name = self.map.name
        self.map_number = self.map.number

