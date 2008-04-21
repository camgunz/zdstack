from decimal import Decimal

from ZDStack.TeamZServ import TeamZServ

class TeamDMZServ(TeamZServ):

    def __init__(self, name, config, zdstack):
        self.ctf = False
        TeamZServ.__init__(self, name, 'teamdm', config, zdstack)

    def get_configuration(self):
        configuration = TeamZServ.get_configuration(self)
        configuration += 'set ctf "0"\n'
        return configuration

