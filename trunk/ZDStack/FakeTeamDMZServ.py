import logging

from ZDStack.Dictable import Dictable
from ZDStack.TeamMap import TeamMap
from ZDStack.BaseTeam import BaseTeam
from ZDStack.TeamPlayer import TeamPlayer
from ZDStack.TeamStats import TeamStats
from ZDStack.FakeZServ import FakeZServ

class FakeTeamDMZServ(FakeZServ):

    """FakeTeamDMZServ represents a FakeZServ configured for TeamDM."""

    def __init__(self, player_class=TeamPlayer, team_class=BaseTeam,
                       map_class=TeamMap, stats_class=TeamStats,
                       log_type='server'):
        """Initializes a FakeTeamDMZServ

        player_class: the player class to use
        team_class:   the team class to use
        map_class:    the map class to use
        stats_class:  the stats class to use (for remembering games)
        log_type:     a string representing the type of log to parse,

        """
        self.ctf = False
        self.team_class = team_class
        FakeZServ.__init__(self, player_class=player_class,
                                 map_class=map_class,
                                 stats_class=stats_class,
                                 log_type=log_type)

    def initialize_general_stats(self):
        FakeZServ.initialize_general_stats(self)
        self.red_team = self.team_class('red')
        self.blue_team = self.team_class('blue')
        self.green_team = self.team_class('green')
        self.white_team = self.team_class('white')
        self.teams = Dictable({'red': self.red_team,
                               'blue': self.blue_team,
                               'green': self.green_team,
                               'white': self.white_team})

    def dump_stats(self):
        return [self.map.export(), self.red_team.export(),
                self.blue_team.export(),self.green_team.export(),
                self.white_team.export(), self.players.export()]

    def get_team(self, color):
        if color not in self.teams:
            raise ValueError("%s team not found" % (color.capitalize()))
        return self.teams[color]

    def change_map(self, map_number, map_name):
        FakeZServ.change_map(self, map_number, map_name)
        for team in self.teams.values():
            team.initialize()
            team.set_map(self.map)

