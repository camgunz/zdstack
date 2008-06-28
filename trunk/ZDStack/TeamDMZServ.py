from decimal import Decimal

from ZDStack.TeamZServ import TeamZServ

class TeamDMZServ(TeamZServ):

    """TeamDMZServ represents a ZServ configured for TeamDM."""

    def __init__(self, name, config, zdstack):
        """Initializes a TeamDMZServ

        name:    a string representing the name of the TeamDMZServ
        config:  a dict of configuration options and values
        zdstack: a Stack instance

        """
        self.ctf = False
        TeamZServ.__init__(self, name, 'teamdm', config, zdstack)

    def get_configuration(self):
        """Returns a string of configuration data."""
        configuration = TeamZServ.get_configuration(self)
        configuration += 'set ctf "0"\n'
        return configuration

