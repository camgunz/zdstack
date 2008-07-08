from ZDStack.Utils import get_ratio
from ZDStack.TeamPlayer import TeamPlayer
from ZDStack.CTFStatKeeper import CTFStatKeeper

class CTFPlayer(TeamPlayer, CTFStatKeeper):

    """CTFPlayer represents a Capture the Flag player."""

    def __init__(self, name, zserv, ip=None):
        """Initializes a CTFPlayer instance.

        name:  a string representing the player's name
        zserv: a ZServ instance
        ip:    optional, a string representing the player's IP address

        """
        TeamPlayer.__init__(self, name, zserv, ip)
        CTFStatKeeper.__init__(self)

    def initialize(self):
        """Initializes this CTFPlayer's stats."""
        TeamPlayer.initialize(self)
        CTFStatKeeper.initialize(self)
        self.total_flag_drops = 0
        self.total_flag_losses = 0
        self.player_flag_drops = {}
        self.weapon_flag_drops = {}
        self.player_weapon_flag_drops = {}
        self.player_flag_losses = {}
        self.weapon_flag_losses = {}
        self.player_weapon_flag_losses = {}

    def _add_weapon(self, weapon):
        """Private method.

        weapon: a string representing the name of a weapon to add

        This method is called on every weapon in self.weapons by
        self.add_weapon.  It exists to be overridden by subclasses.

        """
        TeamPlayer._add_weapon(self, weapon)
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
        TeamPlayer._add_adversary(self, adversary)
        if adversary not in self.player_flag_drops:
            self.player_flag_drops[adversary] = 0
        if adversary not in self.player_flag_losses:
            self.player_flag_losses[adversary] = 0
        if adversary not in self.player_weapon_flag_drops:
            self.player_weapon_flag_drops[adversary] = {}.fromkeys(self.weapons, 0)
        if adversary not in self.player_weapon_flag_losses:
            self.player_weapon_flag_losses[adversary] = {}.fromkeys(self.weapons, 0)

    def add_frag(self, frag):
        TeamPlayer.add_frag(self, frag)
        if frag.fragged_runner:
            self.player_weapon_flag_drops[frag.fraggee][frag.weapon] += 1
            self.player_flag_drops[frag.fraggee] += 1
            self.weapon_flag_drops[frag.weapon] += 1

    def add_death(self, frag):
        TeamPlayer.add_death(self, frag)
        if frag.fragged_runner:
            self.player_weapon_flag_losses[frag.fraggee][frag.weapon] += 1
            self.player_flag_losses[frag.fragger] += 1
            self.weapon_flag_losses[frag.weapon] += 1

    def export_summary(self):
        """Exports a summary of this CTFPlayer's stats."""
        d = self.export()
        s = TeamPlayer.export_summary(self)
        self.flag_touches = 0
        self.flag_returns = 0
        self.flag_picks = 0
        self.flag_caps = 0

