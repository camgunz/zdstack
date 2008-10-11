from ZDStack.FakeDMZServ import FakeDMZServ

class FakeDuelZServ(FakeDMZServ):

    """FakeDuelZServ is a ZServ configured for Dueling."""

    def __init__(self, name):
        """Initializes a FakeDuelZServ.

        name:    a string representing the name of this ZServ

        """
        FakeDMZServ.__init__(self, name, 'duel')

