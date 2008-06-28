from ZDStack.TeamMap import TeamMap
from ZDStack.CTFStatKeeper import CTFStatKeeper

class CTFMap(TeamMap, CTFStatKeeper):

    """CTFMap represents a Capture the Flag map."""

    def __init__(self, number, name):
        """Initializes a CTFMap instance.

        number: a string representing the number of the map
        name:   an int representing the name of the map

        """
        TeamMap.__init__(self, number, name)
        CTFStatKeeper.__init__(self)

    def initialize(self):
        """Initializes stats for this CTFMap."""
        TeamMap.initialize(self)
        CTFStatKeeper.initialize(self)

    def set_map(self, map):
        """Does nothing."""
        pass

    def set_team(self, team):
        """Does nothing."""
        pass

    def set_has_flag(self, has_flag):
        """Does nothing."""
        pass

