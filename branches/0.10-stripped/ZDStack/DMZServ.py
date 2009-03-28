import logging

from ZDStack.BaseZServ import BaseZServ

class DMZServ(BaseZServ):

    """DMZServ is a ZServ configured for Deathmatch."""

    def __init__(self, name, type, config, zdstack):
        """Initializes a DMZServ instance.

        name:    a string representing the name of this zserv
        type:    a string representing the type of this zserv.  Valid
                 options are "coop" "duel" "ffa" "teamdm" and "ctf"
        config:  a dict of configuration options and values
        zdstack: a Stack instance

        """
        self.deathmatch = True
        BaseZServ.__init__(self, name, type, config, zdstack)

    def load_config(self, config):
        """Loads the configuration.

        config: a dict of configuration options and values.

        """
        logging.debug('')
        def is_valid(x):
            return x in config and config[x]
        BaseZServ.load_config(self, config)
        if is_valid('fraglimit'):
            self.fraglimit = int(self.config['fraglimit'])
        elif is_valid(self.type + '_fraglimit'):
            self.fraglimit = int(self.config[self.type + '_fraglimit'])
        self.config['fraglimit'] = self.fraglimit

    def get_configuration(self):
        """Returns a string of configuration data."""
        logging.debug('')
        return BaseZServ.get_configuration(self) + 'set deathmatch "1"\n'

