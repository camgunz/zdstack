from decimal import Decimal

from ZDStack.ZServ import ZServ

class TeamDM(ZServ):

    def __init__(self, name, config, zdstack):
        ZServ.__init__(self, name, config, zdstack)
        self.type = 'teamdm'
        self.deathmatch = True
        self.teamplay = True
        self.ctf = False
        if is_valid('dmflags'):
            self.dmflags = config['dmflags']
        elif is_valid('tdm_dmflags'):
            self.dmflags = config['tdm_dmflags']
        if is_valid('dmflags2'):
            self.dmflags2 = config['dmflags2']
        elif is_valid('tdm_dmflags2'):
            self.dmflags2 = config['tdm_dmflags2']
        if is_valid('teamdamage'):
            self.teamdamage = Decimal(config['teamdamage'])
        elif is_valid('tdm_teamdamage'):
            self.teamdamage = Decimal(config['tdm_teamdamage'])
        if is_valid('max_clients'):
            self.max_clients = int(config['max_clients'])
        elif is_valid('tdm_max_clients'):
            self.max_clients = int(config['tdm_max_clients'])
        if is_valid('max_players'):
            self.max_players = int(config['max_players'])
        elif is_valid('tdm_max_players'):
            self.max_players = int(config['tdm_max_players'])
        if is_valid('max_teams'):
            self.max_teams = int(config['max_teams'])
        elif is_valid('tdm_max_teams'):
            self.max_teams = int(config['tdm_max_teams'])
        if is_valid('max_players_per_team'):
            self.max_players_per_team = int(config['max_players_per_team'])
        elif is_valid('tdm_max_players_per_team'):
            self.max_players_per_team = int(config['tdm_max_players_per_team'])
        if is_valid('timelimit'):
            self.timelimit = int(config['timelimit'])
        elif is_valid('tdm_timelimit'):
            self.timelimit = int(config['tdm_timelimit'])
        if is_valid('scorelimit'):
            self.scorelimit = int(config['scorelimit'])
        elif is_valid('tdm_scorelimit'):
            self.scorelimit = int(config['tdm_scorelimit'])
        config['dmflags'] = self.dmflags
        config['dmflags2'] = self.dmflags2
        config['teamdamage'] = self.teamdamage
        config['max_clients'] = self.max_clients
        config['max_players'] = self.max_players
        config['max_teams'] = self.max_teams
        config['max_players_per_team'] = self.max_players_per_team
        config['timelimit'] = self.timelimit
        config['scorelimit'] = self.scorelimit
        self.configuration = self.get_configuration()
