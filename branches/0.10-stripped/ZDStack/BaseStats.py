from ZDStack.Dictable import Dictable

class BaseStats(Dictable):

    """BaseStats is a container for game stats.

    BaseStats contains stats for a game's:
        * map
        * teams (if applicable)
        * players

    This is only used by ZServ to remember stats

    """

    def __init__(self, map, players={}):
        """Initializes a BaseStats instance.

        map:     a Map instance.
        players: a dict mapping player names to Player instances.

        """
        Dictable.__init__(self)
        self.map = map
        self.name = map['name']
        self.number = map['number']
        self.players = players

    def __str__(self):
        return "<Stats: %s>" % (self.name)

    def __repr__(self):
        return "Stats(%s,[%s])" % (self.name, self.players)

