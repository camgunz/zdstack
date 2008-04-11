from decimal import Decimal

from ZDStack.ZServ import ZServ

class Coop(ZServ):

    def __init__(self, name, config, zdstack):
        def is_valid(x):
            return x in config and config[x]
        def is_yes(x):
            return x in config and yes(x)
        self.deathmatch = False
        self.teamplay = False
        self.ctf = False
        ZServ.__init__(self, name, 'coop', config, zdstack)
        if is_valid('dmflags'):
            self.dmflags = config['dmflags']
        elif is_valid('coop_dmflags'):
            self.dmflags = config['coop_dmflags']
        if is_valid('dmflags2'):
            self.dmflags2 = config['dmflags2']
        elif is_valid('coop_dmflags2'):
            self.dmflags2 = config['coop_dmflags2']
        if is_valid('teamdamage'):
            self.teamdamage = Decimal(config['teamdamage'])
        elif is_valid('coop_teamdamage'):
            self.teamdamage = Decimal(config['coop_teamdamage'])
        if is_valid('max_clients'):
            self.max_clients = int(config['max_clients'])
        elif is_valid('coop_max_clients'):
            self.max_clients = int(config['coop_max_clients'])
        if is_valid('max_players'):
            self.max_players = int(config['max_players'])
        elif is_valid('coop_max_players'):
            self.max_players = int(config['coop_max_players'])
        if is_valid('timelimit'):
            self.timelimit = int(config['timelimit'])
        elif is_valid('coop_timelimit'):
            self.timelimit = int(config['coop_timelimit'])
        config['dmflags'] = self.dmflags
        config['dmflags2'] = self.dmflags2
        config['teamdamage'] = self.teamdamage
        config['max_clients'] = self.max_clients
        config['max_players'] = self.max_players
        config['timelimit'] = self.timelimit
        self.configuration = self.get_configuration()
        write_file(self.configuration, self.configfile, overwrite=True)

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

