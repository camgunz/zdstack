from ZDStack.FakeTeamZServ import FakeTeamZServ

class FakeTeamDMZServ(FakeTeamZServ):

    """FakeTeamDMZServ represents a ZServ configured for TeamDM."""

    def __init__(self, name):
        """Initializes a FakeTeamDMZServ

        name:    a string representing the name of the TeamDMZServ

        """
        self.ctf = False
        FakeTeamZServ.__init__(self, name, 'teamdm')

