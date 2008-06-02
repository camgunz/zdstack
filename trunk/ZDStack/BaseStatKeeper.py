import logging 
from ZDStack.Dictable import Dictable
from ZDStack.Listable import Listable

class BaseStatKeeper(Dictable):

    def __init__(self, stat_container=None):
        self.initialize()
        Dictable.__init__(self)
        self.stat_container = stat_container

    def initialize(self):
        self.frags = Listable()
        self.deaths = Listable()
        self.rcon_actions = Listable()
        self.rcon_denials = 0
        self.rcon_accesses = 0

    def exportables(self):
        exportables = Dictable.exportables(self)
        return [x for x in exportables \
                if not (x[0] == 'stat_container' and x[1] == self.stat_container)]

    def add_frag(self, frag):
        logging.getLogger('').info('')
        self.frags.append(frag)
        if self.stat_container:
            self.stat_container.add_frag(frag)

    def add_death(self, death):
        logging.getLogger('').info('')
        self.deaths.append(death)
        if self.stat_container:
            self.stat_container.add_death(death)

    def add_rcon_denial(self):
        logging.getLogger('').info('')
        self.rcon_denials += 1
        if self.stat_container:
            self.stat_container.add_rcon_denial()

    def add_rcon_access(self):
        logging.getLogger('').info('')
        self.rcon_accesses += 1
        if self.stat_container:
            self.stat_container.add_rcon_access()

    def add_rcon_action(self, rcon_action):
        logging.getLogger('').info('')
        self.rcon_actions.append(rcon_action)
        if self.stat_container:
            self.stat_container.add_rcon_action(rcon_action)

