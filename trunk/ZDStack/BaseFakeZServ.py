import logging
import tempfile

from ZDStack.Dictable import Dictable

from pyfileutils import get_temp_dir, rmtree

class BaseFakeZServ:

    """BaseFakeZServ is a FakeZServ for client log parsing."""

    # There are probably a lot of race conditions here...
    # TODO: add locks, specifically in RPC-accessible methods and
    #       around the data structures they use.

    def __init__(self, name, type):
        """Initializes a BaseZServ instance.

        name:    a string representing the name of this ZServ.
        type:    the game-mode of this ZServ, like 'ctf', 'ffa', etc.

        """
        logging.debug('')
        self.name = name
        self.type = type
        self.homedir = get_temp_dir(dir=tempfile.gettempdir())
        self.extra_exportables_funcs = []

    def __str__(self):
        return "<FakeZServ [%s]>" % (self.name)

    def export(self):
        """Returns a dict of ZServ configuration information."""
        logging.getLogger('').info('')
        d = {'stats_should_go_here': 'whoo stats!'}
        for func, args, kwargs in self.extra_exportables_funcs:
            d = func(*([d] + args), **kwargs)
        return Dictable(d).export()

