import logging

from ZDStack.Listable import Listable
from ZDStack.TeamStatKeeper import TeamStatKeeper

class CTFStatKeeper(TeamStatKeeper):

    """CTFStatKeeper represents the class that keeps CTF stats."""

    def __init__(self):
        """Initializes CTFStatKeeper."""
        TeamStatKeeper.__init__(self)

    def initialize(self):
        """Initializes CTFStatKeeper's stats."""
        self.flag_drops = Listable()
        self.flag_losses = Listable()
        self.total_flag_drops = 0
        self.total_flag_losses = 0
        self.flag_touches = 0
        self.flag_returns = 0
        self.flag_picks = 0
        self.flag_caps = 0
        self.has_flag = False
        TeamStatKeeper.initialize(self)

    def set_has_flag(self, has_flag):
        """Sets the "has_flag" flag.
        
        has_flag: a boolean representing whether this statkeeper has
                  the flag or not.
        
        """
        logging.getLogger('').info('')
        self.has_flag = has_flag
        if self.stat_container:
            self.stat_container.set_has_flag(has_flag)

    def add_flag_touch(self):
        """Adds a flag touch to flag stats."""
        logging.getLogger('').info('')
        self.flag_touches += 1
        if self.stat_container:
            self.stat_container.add_flag_touch()
        self.set_has_flag(True)

    def add_flag_drop(self, flag_drop):
        """Adds a flag drop to flag stats.
        
        flag_drop: a Frag instance.

        """
        logging.getLogger('').info('')
        self.flag_drops.append(flag_drop)
        self.total_flag_drops += 1
        if self.stat_container:
            self.stat_container.add_flag_drop(flag_drop)
        self.set_has_flag(False)

    def add_flag_pick(self):
        """Adds a flag pick to flag stats."""
        logging.getLogger('').info('')
        self.flag_picks += 1
        if self.stat_container:
            self.stat_container.add_flag_pick()
        self.set_has_flag(True)

    def add_flag_return(self):
        """Adds a flag return to flag stats."""
        logging.getLogger('').info('')
        self.flag_returns += 1
        if self.stat_container:
            self.stat_container.add_flag_return()

    def add_flag_loss(self, flag_loss):
        """Adds a flag loss to flag stats.

        flag_loss: a Frag instance.

        """
        logging.getLogger('').info('')
        self.flag_losses.append(flag_loss)
        self.total_flag_drops += 1
        if self.stat_container:
            self.stat_container.add_flag_loss(flag_loss)
        self.set_has_flag(False)

    def add_flag_cap(self):
        """Adds a flag cap to flag stats."""
        logging.getLogger('').info('')
        self.flag_caps += 1
        if self.stat_container:
            self.stat_container.add_flag_cap()
        self.set_has_flag(False)

