import logging

from ZDStack.BaseFakeZServ import BaseFakeZServ

class FakeDMZServ(BaseFakeZServ):

    """DMZServ is a ZServ configured for Deathmatch."""

    def __init__(self, name, type):
        """Initializes a DMZServ instance.

        name:    a string representing the name of this zserv
        type:    a string representing the type of this zserv.  Valid
                 options are "coop" "duel" "ffa" "teamdm" and "ctf"

        """
        logging.debug('')
        self.deathmatch = True
        BaseFakeZServ.__init__(self, name, type)

