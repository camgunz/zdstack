from ZDStack.BaseStats import BaseStats

class CTFStats(BaseStats):

    """CTFStats holds stats for a CTF game."""

    def __init__(self, map, red_team, blue_team, green_team, white_team,
                       players={}):
        """Initializes a CTFStats instance.

        map: a Map instance.
        red_team: a Team instance representing the Red team.
        blue_team: a Team instance representing the Blue team.
        green_team: a Team instance representing the Green team.
        white_team: a Team instance representing the White team.
        players:  a dict mapping player names to Player instances.

        """
        BaseStats.__init__(self, map, players)
        self.name = map['name']
        self.number = map['number']
        self.red_team = red_team
        self.blue_team = blue_team
        self.green_team = green_team
        self.white_team = white_team
        self.teams = {'red': self.red_team,
                      'blue': self.blue_team,
                      'green': self.green_team,
                      'white': self.white_team}

