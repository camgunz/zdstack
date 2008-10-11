from ZDStack.BaseFakeZServ import BaseFakeZServ

class FakeCoopZServ(BaseFakeZServ):

    """FakeCoopZServ represents a ZServ configured for Cooperative play."""

    def __init__(self, name):
        """Initializes a FakeCoopZServ instance.

        name:    a string representing thie ZServ's name

        """
        BaseFakeZServ.__init__(self, name, 'coop')

