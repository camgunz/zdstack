import logging 
from ZDStack.Utils import get_ratio
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
        # logging.getLogger('').debug('')
        self.adversaries = set()
        self.weapons = set()
        self.total_frags = 0
        self.total_deaths = 0
        self.player_frags = {}
        self.weapon_frags = {}
        self.player_weapon_frags = {}
        self.player_deaths = {}
        self.weapon_deaths = {}
        self.player_weapon_deaths = {}
        self.rcon_actions = Listable()
        self.rcon_denials = 0
        self.rcon_accesses = 0

    def exportables(self):
        """Returns a list of strings representing exportable values."""
        exportables = Dictable.exportables(self)
        return [x for x in exportables \
                if not (x[0] == 'stat_container' and x[1] == self.stat_container)]

    def add_adversary(self, adversary):
        """Adds an adversary to frag stats.

        adversary: a string representing the name of an adversary.

        """
        # logging.getLogger('').debug('')
        self.adversaries.add(adversary)
        for a in self.adversaries:
            self._add_adversary(a)

    def _add_adversary(self, adversary):
        """Adds an adversary to frag stats.

        adversary: a string representing the name of an adversary.

        This method is called on every adversary in self.adversaries by
        self.add_adversary.  It exists to be overridden by subclasses.
       
        """
        if adversary not in self.player_frags:
            self.player_frags[adversary] = 0
        if adversary not in self.player_deaths:
            self.player_deaths[adversary] = 0
        if adversary not in self.player_weapon_frags:
            self.player_weapon_frags[adversary] = {}.fromkeys(self.weapons, 0)
        if adversary not in self.player_weapon_deaths:
            self.player_weapon_deaths[adversary] = {}.fromkeys(self.weapons, 0)

    def add_weapon(self, weapon):
        """Adds a weapon to frag stats.

        weapon: a string representing the name of the weapon.

        """
        # logging.getLogger('').debug('')
        self.weapons.add(weapon)
        for weapon in self.weapons:
            self._add_weapon(weapon)

    def _add_weapon(self, weapon):
        """Private method.

        weapon: a string representing the name of a weapon to add

        This method is called on every weapon in self.weapons by
        self.add_weapon.  It exists to be overridden by subclasses.

        """
        if weapon not in self.weapon_frags:
            self.weapon_frags[weapon] = 0
        if weapon not in self.weapon_deaths:
            self.weapon_deaths[weapon] = 0
        for player in self.player_weapon_frags:
            if weapon not in self.player_weapon_frags[player]:
                self.player_weapon_frags[player][weapon] = 0
        for player in self.player_weapon_deaths:
            if weapon not in self.player_weapon_deaths[player]:
                self.player_weapon_deaths[player][weapon] = 0

    def _should_add_adversary(self, adversary):
        """Returns True if an adversary should be added to stats.

        adversary: a string representing the name of an adversary to
                   potentially add

        """
        return not adversary in self.adversaries

    def _should_add_weapon(self, weapon):
        """Returns True if an weapon should be added to stats.

        weapon: a string representing the name of an weapon to
                potentially add

        """
        return not weapon in self.weapons

    def add_frag(self, frag):
        """Adds a frag to frag stats.

        frag: a Frag instance.

        """
        # logging.getLogger('').debug('')
        self.total_frags += 1
        if self._should_add_weapon(frag.weapon):
            self.add_weapon(frag.weapon)
        if self._should_add_adversary(frag.fragger):
            self.add_adversary(frag.fragger)
        if self._should_add_adversary(frag.fraggee):
            self.add_adversary(frag.fraggee)
        self.weapon_frags[frag.weapon] += 1
        self.player_frags[frag.fraggee] += 1
        self.player_weapon_frags[frag.fraggee][frag.weapon] += 1
        if self.stat_container:
            self.stat_container.add_frag(frag)

    def add_death(self, death):
        """Adds a death to frag stats.

        death: a Frag instance.

        """
        # logging.getLogger('').debug('')
        self.total_deaths += 1
        if self._should_add_weapon(death.weapon):
            self.add_weapon(death.weapon)
        if self._should_add_adversary(death.fragger):
            self.add_adversary(death.fragger)
        if self._should_add_adversary(death.fraggee):
            self.add_adversary(death.fraggee)
        self.weapon_deaths[death.weapon] += 1
        self.player_deaths[death.fragger] += 1
        self.player_weapon_deaths[death.fragger][death.weapon] += 1
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

    def get_frag_dict(self):
        """Returns a dict of frag stats."""
        d = {'adversaries': {}.fromkeys(self.adversaries),
             'weapons': {}.fromkeys(self.weapons),
             'frags': self.total_frags,
             'deaths': self.total_deaths,
             'ratio': get_ratio(self.total_frags, self.total_deaths)}
        for a in d['adversaries']:
            d['adversaries'][a] = {'frags': self.player_frags[a],
                                   'deaths': self.player_deaths[a],
                                   'ratio': get_ratio(self.player_frags[a],
                                                      self.player_deaths[a])}
        for weapon in d['weapons']:
            d['weapons'][weapon] = \
                                {'frags': self.weapon_frags[weapon],
                                 'deaths': self.weapon_deaths[weapon],
                                 'ratio': get_ratio(self.weapon_frags[weapon],
                                                    self.weapon_deaths[weapon])}
            for adversary in d['adversaries']:
                if weapon not in d['adversaries'][adversary]:
                    d['adversaries'][adversary][weapon] = {}
                    total_frags = self.player_weapon_frags[adversary][weapon]
                    total_deaths = self.player_weapon_deaths[adversary][weapon]
                    ratio = get_ratio(total_frags, total_deaths)
                    d['adversaries'][adversary][weapon]['frags'] = total_frags
                    d['adversaries'][adversary][weapon]['deaths'] = total_deaths
                    d['adversaries'][adversary][weapon]['ratio'] = ratio
        return d

    def export(self):
        """Exports this player as a dict of info and stats."""
        d = Dictable.export(self)
        d.update(self.get_frag_dict())
        return d

