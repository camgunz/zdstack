from decimal import Decimal

from ZDStack.BaseZServ import BaseZServ

class CoopZServ(BaseZServ):

    """CoopZServ represents a ZServ configured for Cooperative play."""

    def __init__(self, name, config, zdstack):
        """Initializes a CoopZServ instance.

        name:    a string representing thie ZServ's name
        config:  a dict of configuration options and values
        zdstack: a Stack instance

        """
        BaseZServ.__init__(self, name, 'coop', config, zdstack)

    def load_config(self, config):
        """Loads the configuration.

        config: a dict of configuration options and values

        """
        def is_valid(x):
            return x in config and config[x]
        BaseZServ.load_config(self, config)
        self.teamdamage = None
        if is_valid('teamdamage'):
            self.teamdamage = Decimal(self.config['teamdamage'])
        elif is_valid('coop_teamdamage'):
            self.teamdamage = Decimal(self.config['coop_teamdamage'])
        self.config['teamdamage'] = self.teamdamage

    def get_configuration(self):
        """Returns a string of configuration data."""
        configuration = BaseZServ.get_configuration(self)
        configuration += 'set deathmatch "0"\n'
        configuration += 'set teamplay "0"\n'
        configuration += 'set ctf "0"\n'
        if self.teamdamage:
            configuration += 'set teamdamage "%s"\n' % (self.teamdamage)
        return configuration

