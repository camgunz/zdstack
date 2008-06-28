import logging 
from ZDStack.Dictable import Dictable
from ZDStack.Listable import Listable

class BaseStatKeeper(Dictable):

    """BaseStatKeeper keeps stats, and exports them as a dict.

    BaseStatKeeper will also hold a stat_container... which is also an
    instance or subclass of BaseStatKeeper.  BaseStatKeeper's methods
    update its stat_container's stats as well, unless overridden not
    to.

    """

    def __init__(self, stat_container=None):
        """Initializes BaseStatKeeper.

        stat_container: an instance or subclass of BaseStatKeeper

        """
        self.initialize()
        Dictable.__init__(self)
        self.stat_container = stat_container

    def initialize(self):
        """Initializes BaseStatKeeper's stats."""
        self.frags = Listable()
        self.deaths = Listable()
        self.rcon_actions = Listable()
        self.rcon_denials = 0
        self.rcon_accesses = 0

    def exportables(self):
        """Returns a list of strings representing exportable values."""
        exportables = Dictable.exportables(self)
        return [x for x in exportables \
                if not (x[0] == 'stat_container' and x[1] == self.stat_container)]

    def add_frag(self, frag):
        """Adds a frag to stats.

        frag: a Frag instance

        """
        logging.getLogger('').info('')
        self.frags.append(frag)
        if self.stat_container:
            self.stat_container.add_frag(frag)

    def add_death(self, death):
        """Adds a death to stats.

        fragFrag instance.

        """
        logging.getLogger('').info('')
        self.deaths.append(death)
        if self.stat_container:
            self.stat_container.add_death(death)

    def add_rcon_denial(self):
        """Adds an RCON denial to stats."""
        logging.getLogger('').info('')
        self.rcon_denials += 1
        if self.stat_container:
            self.stat_container.add_rcon_denial()

    def add_rcon_access(self):
        """Adds an RCON access to stats."""
        logging.getLogger('').info('')
        self.rcon_accesses += 1
        if self.stat_container:
            self.stat_container.add_rcon_access()

    def add_rcon_action(self, rcon_action):
        """Adds an RCON access to stats.
        
        rcon_action: a string representing the name of the action
        
        """
        logging.getLogger('').info('')
        self.rcon_actions.append(rcon_action)
        if self.stat_container:
            self.stat_container.add_rcon_action(rcon_action)

