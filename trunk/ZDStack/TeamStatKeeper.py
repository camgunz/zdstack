import logging

from ZDStack import log
from ZDStack.BaseStatKeeper import BaseStatKeeper

class TeamStatKeeper(BaseStatKeeper):

    def __init__(self, stat_container=None):
        logging.getLogger('').debug('')
        BaseStatKeeper.__init__(self, stat_container)
        self.set_team(stat_container)

    def initialize(self):
        logging.getLogger('').debug('')
        self.map = None
        BaseStatKeeper.initialize(self)

    def _log_items(self, x):
        s = "TeamStatKeeper: x: items: [%s]"
        t = (', '.join([str(x) for x in self.items()]))
        logging.getLogger('').debug(s % t)

    def set_map(self, map):
        logging.getLogger('').debug('')
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
        logging.getLogger('').debug('')
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
        # self._log_items('exportables')
        exportables = BaseStatKeeper.exportables(self)
        return [x for x in exportables if not (x[0] == 'map' and x[1] == self.map)]

