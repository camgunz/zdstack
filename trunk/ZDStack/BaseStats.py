from ZDStack.Dictable import Dictable

class BaseStats(Dictable):

    def __init__(self, map, players={}):
        Dictable.__init__(self)
        self.map = map
        self.name = map['name']
        self.number = map['number']
        self.players = players

