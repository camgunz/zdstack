import logging

from decimal import Decimal

from ZDStack.TeamZServ import TeamZServ

class CTFZServ(TeamZServ):

    def __init__(self, name, config, zdstack):
        self.ctf = True
        TeamZServ.__init__(self, name, 'ctf', config, zdstack)

    def get_configuration(self):
        logging.getLogger('').info('')
        configuration = TeamZServ.get_configuration(self)
        configuration += 'set ctf "1"\n'
        return configuration

