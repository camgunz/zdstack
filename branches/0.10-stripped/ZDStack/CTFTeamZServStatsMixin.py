from ZDStack.CTFMap import CTFMap
from ZDStack.CTFTeam import CTFTeam
from ZDStack.CTFStats import CTFStats
from ZDStack.CTFPlayer import CTFPlayer
from ZDStack.TeamZServStatsMixin import TeamZServStatsMixin

class CTFTeamZServStatsMixin(TeamZServStatsMixin):

    """CTFTeamZServStatsMixin Adds CTF and Team stats to a ZServ."""

    def __init__(self, memory_slots, load_plugins=False, log_type='server'):
        """Initializes a CTFTeamZServStatsMixin instance.

        memory_slots: an int representing the number of maps to
                      remember.
        load_plugins: a boolean representing whether or not to load
                      plugins.
        log_type:     a string representing the type of logfile to
                      parse, valid possibilities are "server" and
                      "client"

        """
        map_class = CTFMap
        team_class = CTFTeam
        stats_class = CTFStats
        player_class = CTFPlayer
        TeamZServStatsMixin.__init__(self, memory_slots, player_class,
                                           team_class, map_class, stats_class,
                                           log_type)

