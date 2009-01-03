import logging

from ZDStack.Dictable import Dictable
from ZDStack.TeamMap import TeamMap
from ZDStack.BaseTeam import BaseTeam
from ZDStack.TeamPlayer import TeamPlayer
from ZDStack.TeamStats import TeamStats
from ZDStack.GeneralZServStatsMixin import GeneralZServStatsMixin

class TeamZServStatsMixin(GeneralZServStatsMixin):

    """TeamZServStatsMixin adds team stats to a ZServ."""

    def __init__(self, memory_slots, player_class=TeamPlayer,
                                     team_class=BaseTeam,
                                     map_class=TeamMap,
                                     stats_class=TeamStats,
                                     load_plugins=False,
                                     log_type='server'):
        """Initializes a TeamZServStatsMixin.

        memory_slots: an int representing the number of games to
                      remember
        player_class: the player class to use
        team_class:   the team class to use
        map_class:    the map class to use
        stats_class:  the stats class to use (for remembering games)
        load_plugins: a boolean, whether or not to load plugins
        log_type:     a string representing the type of log to parse,
                      valid options are 'server' and 'client'

        """
        self.team_class = team_class
        GeneralZServStatsMixin.__init__(self, memory_slots, player_class,
                                              map_class, stats_class, log_type)

    def initialize_general_stats(self):
        """Initializes stats from the general log."""
        logging.debug('')
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
        """Returns a list of dumped stats from all StatKeepers."""
        logging.debug('')
        return [self.map.export(), self.red_team.export(),
                self.blue_team.export(), self.green_team.export(),
                self.white_team.export(), self.players.export()]

    def get_team(self, color):
        """Returns a Team.

        color: a string representing the color of the Team to return

        """
        logging.debug('')
        if color not in self.teams:
            # Maybe we should make custom exceptions like TeamNotFoundError
            raise ValueError("%s team not found" % (color.capitalize()))
        return self.teams[color]

    def change_map(self, map_number, map_name):
        """Handles a map change event.

        map_number: an int representing the number of the new map
        map_name:   a string representing the name of the new map

        """
        logging.debug('')
        GeneralZServStatsMixin.change_map(self, map_number, map_name)
        for team in self.teams.values():
            team.initialize()
            team.set_map(self.map)

