from ZDStack.DMZServ import DMZServ

class DuelZServ(DMZServ):

    """DuelZServ is a ZServ configured for Dueling."""

    def __init__(self, name, config, zdstack):
        """Initializes a DuelZServ.

        name:    a string representing the name of this ZServ
        config:  a dict of configuration options and values
        zdstack: a Stack instance

        """
        DMZServ.__init__(self, name, 'duel', config, zdstack)

    def load_config(self, config):
        """Loads the configuration.

        config: a dict of configuration options and values.

        """
        DMZServ.load_config(self, config)
        self.max_players = 2
        config['max_players'] = self.max_players

