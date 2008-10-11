from ZDStack.FakeDMZServ import FakeDMZServ

class FakeFFAZServ(FakeDMZServ):

    """FakeFFAZServ is a ZServ configured for Free-For-All."""

    def __init__(self, name):
        """Initializes a FakeFFAZServ.

        name:    a string representing the name of this ZServ

        """
        FakeDMZServ.__init__(self, name, 'ffa')

