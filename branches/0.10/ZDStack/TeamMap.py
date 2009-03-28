from ZDStack.BaseMap import BaseMap
from ZDStack.TeamStatKeeper import TeamStatKeeper

class TeamMap(BaseMap, TeamStatKeeper):

    """TeamMap represents a map in a Team game."""

    def __init__(self, number, name):
        """Initializes a TeamMap.

        number: an int representing the number of the map
        name:   a string representing the name of the map

        """
        BaseMap.__init__(self, number, name)
        TeamStatKeeper.__init__(self)

