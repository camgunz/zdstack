import logging
from ZDStack.Dictable import Dictable

class FakeZServ:

    """BaseFakeZServ is a FakeZServ for client log parsing."""

    # There are probably a lot of race conditions here...
    # TODO: add locks, specifically in RPC-accessible methods and
    #       around the data structures they use.

    def __init__(self, name, type):
        """Initializes a BaseZServ instance.

        name:    a string representing the name of this ZServ.
        type:    the game-mode of this ZServ, like 'ctf', 'ffa', etc.

        """
        self.name = name
        self.type = type

    def __str__(self):
        return "<ZServ [%s:%d]>" % (self.name, self.port)

    def export(self):
        """Returns a dict of ZServ configuration information."""
        logging.getLogger('').info('')
        d = {'stats_should_go_here': 'whoo stats!'}
        return Dictable(d).export()

