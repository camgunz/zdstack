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
        self.total_flag_drops = 0
        self.total_flag_losses = 0
        self.player_flag_drops = {}
        self.weapon_flag_drops = {}
        self.player_weapon_flag_drops = {}
        self.player_flag_losses = {}
        self.weapon_flag_losses = {}
        self.player_weapon_flag_losses = {}
        self.flag_touches = 0
        self.flag_returns = 0
        self.flag_picks = 0
        self.flag_caps = 0
        self.has_flag = False
        TeamStatKeeper.initialize(self)

    def _add_weapon(self, weapon):
        """Private method.

        weapon: a string representing the name of a weapon to add

        This method is called on every weapon in self.weapons by
        self.add_weapon.  It exists to be overridden by subclasses.

        """
        TeamStatKeeper._add_weapon(self, weapon)
        if weapon not in self.weapon_flag_drops:
            self.weapon_flag_drops[weapon] = 0
        if weapon not in self.weapon_flag_losses:
            self.weapon_flag_losses[weapon] = 0
        for player in self.player_weapon_flag_drops:
            if weapon not in self.player_weapon_flag_drops[player]:
                self.player_weapon_flag_drops[player][weapon] = 0
        for player in self.player_weapon_flag_losses:
            if weapon not in self.player_weapon_flag_losses[player]:
                self.player_weapon_flag_losses[player][weapon] = 0

    def _add_adversary(self, adversary):
        """Adds an adversary to frag stats.

        adversary: a string representing the name of an adversary.

        This method is called on every adversary in self.adversaries by
        self.add_adversary.  It exists to be overridden by subclasses.
       
        """
        TeamStatKeeper._add_adversary(self, adversary)
        if adversary not in self.player_flag_drops:
            self.player_flag_drops[adversary] = 0
        if adversary not in self.player_flag_losses:
            self.player_flag_losses[adversary] = 0
        if adversary not in self.player_weapon_flag_drops:
            self.player_weapon_flag_drops[adversary] = {}.fromkeys(self.weapons, 0)
        if adversary not in self.player_weapon_flag_losses:
            self.player_weapon_flag_losses[adversary] = {}.fromkeys(self.weapons, 0)

    def add_frag(self, frag):
        TeamStatKeeper.add_frag(self, frag)
        if frag.fragged_runner:
            self.player_weapon_flag_drops[frag.fraggee][frag.weapon] += 1
            self.player_flag_drops[frag.fraggee] += 1
            self.weapon_flag_drops[frag.weapon] += 1
            if frag.fraggee != self.name: # no suicide flag drops
                self.total_flag_drops += 1

    def add_death(self, frag):
        TeamStatKeeper.add_death(self, frag)
        if frag.fragged_runner:
            self.player_weapon_flag_losses[frag.fraggee][frag.weapon] += 1
            self.player_flag_losses[frag.fragger] += 1
            self.weapon_flag_losses[frag.weapon] += 1
            self.total_flag_losses += 1

    def set_has_flag(self, has_flag):
        """Sets the "has_flag" flag.
        
        has_flag: a boolean representing whether this statkeeper has
                  the flag or not.
        
        """
        logging.debug('')
        self.has_flag = has_flag
        if self.stat_container:
            self.stat_container.set_has_flag(has_flag)

    def add_flag_touch(self):
        """Adds a flag touch to flag stats."""
        logging.debug('')
        self.flag_touches += 1
        if self.stat_container:
            self.stat_container.add_flag_touch()
        self.set_has_flag(True)

    def add_flag_drop(self, flag_drop):
        """Adds a flag drop to flag stats.
        
        flag_drop: a Frag instance.

        """
        logging.debug('')
        self.total_flag_drops += 1
        if self.stat_container:
            self.stat_container.add_flag_drop(flag_drop)
        self.set_has_flag(False)

    def add_flag_pick(self):
        """Adds a flag pick to flag stats."""
        logging.debug('')
        self.flag_picks += 1
        if self.stat_container:
            self.stat_container.add_flag_pick()
        self.set_has_flag(True)

    def add_flag_return(self):
        """Adds a flag return to flag stats."""
        logging.debug('')
        self.flag_returns += 1
        if self.stat_container:
            self.stat_container.add_flag_return()

    def add_flag_loss(self, flag_loss):
        """Adds a flag loss to flag stats.

        flag_loss: a Frag instance.

        """
        logging.debug('')
        self.total_flag_losses += 1
        if self.stat_container:
            self.stat_container.add_flag_loss(flag_loss)
        self.set_has_flag(False)

    def add_flag_cap(self):
        """Adds a flag cap to flag stats."""
        logging.debug('')
        self.flag_caps += 1
        if self.stat_container:
            self.stat_container.add_flag_cap()
        self.set_has_flag(False)

