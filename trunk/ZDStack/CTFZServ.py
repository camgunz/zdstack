import logging

from decimal import Decimal

from ZDStack.TeamZServ import TeamZServ

class CTFZServ(TeamZServ):

    """CTFZServ represents a ZServ configured for Capture the Flag."""

    def __init__(self, name, config, zdstack):
        """Initializes a CTFZServ instance.

        name:    a string representing the name of this ZServ.
        config:  a dict of configuration options and values.
        zdstack: a Stack instance.

        """
        self.ctf = True
        TeamZServ.__init__(self, name, 'ctf', config, zdstack)

    def get_configuration(self):
        """Returns a string of configuration data."""
        logging.getLogger('').info('')
        configuration = TeamZServ.get_configuration(self)
        configuration += 'set ctf "1"\n'
        return configuration

