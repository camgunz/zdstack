from ZDStack.BaseTeam import BaseTeam
from ZDStack.CTFStatKeeper import CTFStatKeeper

class CTFTeam(BaseTeam, CTFStatKeeper):

    """CTFTeam represents a Capture the Flag team."""

    def __init__(self, color):
        """Initializes a CTFTeam instance.

        color: a string representing the color of the team.
        
        """
        BaseTeam.__init__(self, color)
        CTFStatKeeper.__init__(self)

    def initialize(self):
        """Initializes CTFTeam's stats."""
        BaseTeam.initialize(self)
        CTFStatKeeper.initialize(self)

