from decimal import Decimal

from ZDStack import debug
from ZDStack.DMZServ import DMZServ

class TeamZServ(DMZServ):

    def __init__(self, name, type, config, zdstack):
        DMZServ.__init__(self, name, type, config, zdstack)
        def add_team_info(d):
            d['max_teams'] = self.max_teams
            d['max_players_per_team'] = self.max_players_per_team
            d['teamdamage'] = self.teamdamage
            return d
        self.extra_exportables_funcs.append((add_team_info, [], {}))

    def load_config(self, config):
        debug()
        def is_valid(x):
            return x in config and config[x]
        def is_yes(x):
            return x in config and yes(x)
        DMZServ.load_config(self, config)
        self.max_teams = None
        self.max_players_per_team = None
        self.scorelimit = None
        self.fraglimit = None
        if is_valid('teamdamage'):
            self.teamdamage = Decimal(config['teamdamage'])
        elif is_valid(self.type + '_teamdamage'):
            self.teamdamage = Decimal(config[self.type + '_teamdamage'])
        if is_valid('max_teams'):
            self.max_teams = int(config['max_teams'])
        elif is_valid(self.type + '_max_teams'):
            self.max_teams = int(config[self.type + '_max_teams'])
        if is_valid('max_players_per_team'):
            self.max_players_per_team = int(config['max_players_per_team'])
        elif is_valid(self.type + '_max_players_per_team'):
            self.max_players_per_team = \
                            int(config[self.type + '_max_players_per_team'])
        if is_valid('team_score_limit'):
            self.scorelimit = int(config['team_score_limit'])
        elif is_valid(self.type + '_team_score_limit'):
            self.scorelimit = int(config[self.type + '_team_score_limit'])
        config['teamdamage'] = self.teamdamage
        config['max_teams'] = self.max_teams
        config['max_players_per_team'] = self.max_players_per_team
        config['scorelimit'] = self.scorelimit

    def get_configuration(self):
        debug()
        template = DMZServ.get_configuration(self) + 'set teamplay "1"\n'
        if self.max_teams:
            template += 'set maxteams "%s"\n' % (self.max_teams)
        if self.max_players_per_team:
            template += 'set maxplayersperteam "%s"\n' % \
                                                    (self.max_players_per_team)
        if self.teamdamage:
            template += 'set teamdamage "%s"\n' % (self.teamdamage)
        if self.scorelimit:
            template += 'set teamscorelimit "%s"\n' % (self.scorelimit)
        return template

