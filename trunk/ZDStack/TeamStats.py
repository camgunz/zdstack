from ZDStack.BaseStats import BaseStats

class TeamStats(BaseStats):

    """TeamStats represents Team-based stats."""

    def __init__(self, map, red_team, blue_team, green_team, white_team,
                       players={}):
        """Initializes TeamStats.

        map:        a Map instance
        red_team:   a Team instance representing the red team
        blue_team:  a Team instance representing the blue team
        green_team: a Team instance representing the green team
        white_team: a Team instance representing the white team
        players:    a dict mapping player names to Player instances

        """
        BaseStats.__init__(self, map, players)
        self.red_team = red_team
        self.blue_team = blue_team
        self.green_team = green_team
        self.white_team = white_team
        self.teams = {'red': self.red_team,
                      'blue': self.blue_team,
                      'green': self.green_team,
                      'white': self.white_team}

