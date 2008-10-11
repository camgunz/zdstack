import logging

from ZDStack.FakeDMZServ import FakeDMZServ

class FakeTeamZServ(FakeDMZServ):

    """FakeTeamZServ is a ZServ configured for team play."""

    def __init__(self, name, type):
        """Initializes FakeTeamZServ.

        name:    a string representing the name of this ZServ
        type:    a string representing the type of thie ZServ.  Valid
                 options are 'teamdm' and 'ctf'

        """
        logging.debug('')
        FakeDMZServ.__init__(self, name, type)
        def add_team_info(d):
            d['max_teams'] = self.max_teams
            d['max_players_per_team'] = self.max_players_per_team
            d['teamdamage'] = self.teamdamage
            return d
        self.extra_exportables_funcs.append((add_team_info, [], {}))

