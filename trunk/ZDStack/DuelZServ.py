from ZDStack.DMZServ import DMZServ

class DuelZServ(DMZServ):

    def __init__(self, name, config, zdstack):
        DMZServ.__init__(self, name, 'duel', config, zdstack)

    def load_config(self, config):
        DMZServ.load_config(self, config)
        self.max_players = 2
        config['max_players'] = self.max_players

