from ZDStack.BaseStats import BaseStats

class CTFStats(BaseStats):

    def __init__(self, map, red_team, blue_team, green_team, white_team,
                       players={}):
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

