from ZDStack.DMZServ import DMZServ

class FFAZServ(DMZServ):

    """FFAZServ is a ZServ configured for Free-For-All."""

    def __init__(self, name, config, zdstack):
        """Initializes a FFAZServ.

        name:    a string representing the name of this ZServ
        config:  a dict of configuration options and values
        zdstack: a Stack instance

        """
        DMZServ.__init__(self, name, 'ffa', config, zdstack)

