from decimal import Decimal

from ZDStack.ZServ import ZServ

class Duel(ZServ):

    def __init__(self, name, config, zdstack):
        ZServ.__init__(self, name, config, zdstack)
        self.type = 'duel'
        self.deathmatch = True
        self.teamplay = False
        self.ctf = False
        if is_valid('dmflags'):
            self.dmflags = config['dmflags']
        elif is_valid('duel_dmflags'):
            self.dmflags = config['duel_dmflags']
        elif is_valid('duel_dmflags'):
            self.dmflags = config['duel_dmflags']
        if is_valid('dmflags2'):
            self.dmflags2 = config['dmflags2']
        elif is_valid('duel_dmflags2'):
            self.dmflags2 = config['duel_dmflags2']
        elif is_valid('1-on-1_dmflags2'):
            self.dmflags2 = config['1-on-1_dmflags2']
        if is_valid('max_clients'):
            self.max_clients = int(config['max_clients'])
        elif is_valid('duel_max_clients'):
            self.max_clients = int(config['duel_max_clients'])
        elif is_valid('1-on-1_max_clients'):
            self.max_clients = int(config['1-on-1_max_clients'])
        ###
        # I could offer the ability to have a different number of maximum
        # players... but then it wouldn't be a duel.  If someone wants, say,
        # a 3-way FFA then they can reduce a FFA down to 3 players.
        #
        # if is_valid('max_players'):
        #     self.max_players = int(config['max_players'])
        # elif is_valid('duel_max_players'):
        #     self.max_players = int(config['duel_max_players'])
        # elif is_valid('1-on-1_max_players'):
        #     self.max_players = int(config['1-on-1_max_players'])
        #
        ###
        self.max_players = 2
        if is_valid('timelimit'):
            self.timelimit = int(config['timelimit'])
        elif is_valid('duel_timelimit'):
            self.timelimit = int(config['duel_timelimit'])
        elif is_valid('1-on-1_timelimit'):
            self.timelimit = int(config['1-on-1_timelimit'])
        if is_valid('fraglimit'):
            self.fraglimit = int(config['fraglimit'])
        elif is_valid('duel_fraglimit'):
            self.fraglimit = int(config['duel_fraglimit'])
        elif is_valid('1-on-1_fraglimit'):
            self.fraglimit = int(config['1-on-1_fraglimit'])
        config['dmflags'] = self.dmflags
        config['dmflags2'] = self.dmflags2
        config['max_clients'] = self.max_clients
        config['max_players'] = self.max_players
        config['timelimit'] = self.timelimit
        config['fraglimit'] = self.fraglimit
        self.configuration = self.get_configuration()
