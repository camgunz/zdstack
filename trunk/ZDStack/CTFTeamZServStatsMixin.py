from ZDStack.CTFMap import CTFMap
from ZDStack.CTFTeam import CTFTeam
from ZDStack.CTFStats import CTFStats
from ZDStack.CTFPlayer import CTFPlayer
from ZDStack.TeamZServStatsMixin import TeamZServStatsMixin

class CTFTeamZServStatsMixin(TeamZServStatsMixin):
    def __init__(self, memory_slots, log_type='server'):
        map_class = CTFMap
        team_class = CTFTeam
        stats_class = CTFStats
        player_class = CTFPlayer
        TeamZServStatsMixin.__init__(self, memory_slots, player_class,
                                           team_class, map_class, stats_class,
                                           log_type)

