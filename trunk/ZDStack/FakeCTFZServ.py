import logging
from ZDStack.CTFMap import CTFMap
from ZDStack.CTFTeam import CTFTeam
from ZDStack.CTFStats import CTFStats
from ZDStack.CTFPlayer import CTFPlayer
from ZDStack.FakeTeamDMZServ import FakeTeamDMZServ

class FakeCTFZServ(FakeTeamDMZServ):

    """FakeCTFZServ represents a FakeZServ configured for CTF."""

    def __init__(self, player_class=CTFPlayer, team_class=CTFTeam,
                       map_class=CTFMap, stats_class=CTFStats,
                       log_type='server'):
        """Initializes a FakeCTFZServ instance.

        player_class: the player class to use
        team_class:   the team class to use
        map_class:    the map class to use
        stats_class:  the stats class to use (for remembering games)
        log_type:     a string representing the type of log to parse,

        """
        logging.debug('')
        self.ctf = True
        FakeTeamDMZServ.__init__(self, player_class=player_class,
                                       team_class=team_class,
                                       map_class=map_class,
                                       stats_class=stats_class,
                                       log_type=log_type)
        

