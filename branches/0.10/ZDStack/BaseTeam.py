import logging

from ZDStack.TeamStatKeeper import TeamStatKeeper

class BaseTeam(TeamStatKeeper):

    """BaseTeam represents the base Team class."""

    def __init__(self, color):
        """Initializes a BaseTeam instance.

        color: a string representing this team's color.

        """
        # logging.debug('')
        TeamStatKeeper.__init__(self)
        self.name = color
        self.color = color

    def set_team(self, team):
        """Normally this sets the team for stats... but not for a team."""
        pass

    def set_map(self, map):
        """Sets this team's Map.

        map: a Map instance.

        """
        # logging.debug('')
        self.map = map
        self.stat_container = map

