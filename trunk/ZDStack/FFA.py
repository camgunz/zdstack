from decimal import Decimal

from ZDStack.ZServ import ZServ

class FFA(ZServ):

    def __init__(self, name, config, zdstack):
        self.deathmatch = True
        self.teamplay = False
        self.ctf = False
        ZServ.__init__(self, name, 'ffa', config, zdstack)

    def load_config(self, config):
        def is_valid(x):
            return x in config and config[x]
        def is_yes(x):
            return x in config and yes(x)
        ZServ.load_config(self, config)
        if is_valid('dmflags'):
            self.dmflags = config['dmflags']
        elif is_valid('ffa_dmflags'):
            self.dmflags = config['ffa_dmflags']
        if is_valid('dmflags2'):
            self.dmflags2 = config['dmflags2']
        elif is_valid('ffa_dmflags2'):
            self.dmflags2 = config['ffa_dmflags2']
        if is_valid('max_clients'):
            self.max_clients = int(config['max_clients'])
        elif is_valid('ffa_max_clients'):
            self.max_clients = int(config['ffa_max_clients'])
        if is_valid('max_players'):
            self.max_players = int(config['max_players'])
        elif is_valid('ffa_max_players'):
            self.max_players = int(config['ffa_max_players'])
        if is_valid('timelimit'):
            self.timelimit = int(config['timelimit'])
        elif is_valid('ffa_timelimit'):
            self.timelimit = int(config['ffa_timelimit'])
        if is_valid('fraglimit'):
            self.fraglimit = int(config['fraglimit'])
        elif is_valid('ffa_fraglimit'):
            self.fraglimit = int(config['ffa_fraglimit'])
        config['dmflags'] = self.dmflags
        config['dmflags2'] = self.dmflags2
        config['max_clients'] = self.max_clients
        config['max_players'] = self.max_players
        config['timelimit'] = self.timelimit
        config['fraglimit'] = self.fraglimit

    def get_configuration(self):
        configuration = ZServ.get_configuration(self)
        if self.deathmatch:
            configuration += 'set deathmatch "1"\n'
        else:
            configuration += 'set deathmatch "0"\n'
        if self.teamplay:
            configuration += 'set teamplay "1"\n'
        else:
            configuration += 'set teamplay "0"\n'
        if self.ctf:
            configuration += 'set ctf "1"\n'
        else:
            configuration += 'set ctf "0"\n'
        return configuration

