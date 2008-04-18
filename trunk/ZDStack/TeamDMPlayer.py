from ZDStack.BasePlayer import BasePlayer

class TeamDMPlayer(BasePlayer):

    def __init__(self, name, zserv, ip=None):
        BasePlayer.__init__(self, name, zserv, ip)
        self.team = None
        if self.team is not None:
            self.color = self.team.color
        else:
            self.color = None

    def set_map(self, map):
        self.map = map

    def set_team(self, team):
        self.team = team
        if self.team is not None:
            self.color = self.team.color
        else:
            self.color = None
        self.stat_container = self.team

