import logging

from ZDStack.BaseStatKeeper import BaseStatKeeper

class TeamStatKeeper(BaseStatKeeper):

    """TeamStatKeeper keeps team stats."""

    def __init__(self, stat_container=None):
        """Initializes a TeamStatKeeper.

        stat_container: an instance or subclass of BaseStatKeeper

        """
        # logging.getLogger('').debug('')
        BaseStatKeeper.__init__(self, stat_container)
        self.set_team(stat_container)

    def initialize(self):
        """Initializes TeamStatKeeper's stats."""
        # logging.getLogger('').debug('')
        self.map = None
        BaseStatKeeper.initialize(self)

    def _log_items(self, x):
        """Debugging function, pay no mind."""
        s = "TeamStatKeeper: x: items: [%s]"
        t = (', '.join([str(x) for x in self.items()]))
        logging.getLogger('').debug(s % t)

    def set_map(self, map):
        """Sets TeamStatKeeper's map.

        map: a Map instance.

        """
        # logging.getLogger('').debug('')
        # self._log_items('pre-set_map')
        self.map = map
        if self.team is None:
            self.stat_container = self.map
        if self.map:
            self.map_name = self.map.name
            self.map_number = self.map.number
        else:
            self.map_name = None
            self.map_number = None
        # self._log_items('post-set_map')

    def set_team(self, team):
        """Sets TeamStatKeeper's team.

        team: a Team instance.

        """
        # logging.getLogger('').debug('')
        # self._log_items('pre-set_team')
        self.team = team
        if self.team is not None:
            self.color = self.team.color
            self.stat_container = self.team
        else:
            self.color = None
            self.stat_container = self.map
        # self._log_items('post-set_team')

    def exportables(self):
        """Returns a list of strings representing exportable attributes."""
        # self._log_items('exportables')
        exportables = BaseStatKeeper.exportables(self)
        return [x for x in exportables if not (x[0] == 'map' and x[1] == self.map)]

