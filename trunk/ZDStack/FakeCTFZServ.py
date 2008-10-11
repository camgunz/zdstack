import logging
from ZDStack.FakeTeamZServ import FakeTeamZServ

class FakeCTFZServ(FakeTeamZServ):

    """CTFZServ represents a ZServ configured for Capture the Flag."""

    def __init__(self, name):
        """Initializes a CTFZServ instance.

        name:    a string representing the name of this ZServ.

        """
        logging.debug('')
        self.ctf = True
        FakeTeamZServ.__init__(self, name, 'ctf')

