import logging

from ZDStack.Dictable import Dictable
from ZDStack.TeamMap import TeamMap
from ZDStack.BaseTeam import BaseTeam
from ZDStack.TeamPlayer import TeamPlayer
from ZDStack.TeamStats import TeamStats
from ZDStack.GeneralZServStatsMixin import GeneralZServStatsMixin

class TeamZServStatsMixin(GeneralZServStatsMixin):

    def __init__(self, memory_slots, player_class=TeamPlayer,
                                     team_class=BaseTeam,
                                     map_class=TeamMap,
                                     stats_class=TeamStats,
                                     load_plugins=False,
                                     log_type='server'):
        self.team_class = team_class
        GeneralZServStatsMixin.__init__(self, memory_slots, player_class,
                                              map_class, stats_class, log_type)

    def initialize_general_stats(self):
        logging.getLogger('').info('')
        GeneralZServStatsMixin.initialize_general_stats(self)
        self.red_team = self.team_class('red')
        self.blue_team = self.team_class('blue')
        self.green_team = self.team_class('green')
        self.white_team = self.team_class('white')
        self.teams = Dictable({'red': self.red_team,
                               'blue': self.blue_team,
                               'green': self.green_team,
                               'white': self.white_team})

    def dump_stats(self):
        logging.getLogger('').info('')
        return [self.map.export(), self.red_team.export(),
                self.blue_team.export(), self.green_team.export(),
                self.white_team.export(), self.players.export()]

    def get_team(self, color):
        logging.getLogger('').info('')
        if color not in self.teams:
            # Maybe we should make custom exceptions like TeamNotFoundError
            raise ValueError("%s team not found" % (color.capitalize()))
        return self.teams[color]

    def change_map(self, map_number, map_name):
        logging.getLogger('').info('')
        GeneralZServStatsMixin.change_map(self, map_number, map_name)
        for team in self.teams.values():
            team.initialize()
            team.set_map(self.map)

