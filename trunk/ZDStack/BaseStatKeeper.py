from ZDStack.Dictable import Dictable

class BaseStatKeeper(Dictable):

    def __init__(self, stat_container=None):
        self.frags = Listable()
        self.deaths = Listable()
        self.flag_drops = Listable()
        self.flag_losses = Listable()
        self.rcon_actions = Listable()
        self.rcon_denials = 0
        self.rcon_accesses = 0
        self.flag_returns = 0
        self.flag_caps = 0
        self.stat_container = stat_container

    def add_frag(self, frag):
        self.frags.append(frag)
        if self.stat_container:
            self.stat_container.add_frag(frag)

    def add_death(self, death):
        self.deaths.append(death)
        if self.stat_container:
            self.stat_container.add_death(death)

    def add_rcon_denial(self):
        self.rcon_denials += 1
        if self.stat_container:
            self.stat_container.add_rcon_denial()

    def add_rcon_access(self):
        self.rcon_accesses += 1
        if self.stat_container:
            self.stat_container.add_rcon_access()

    def add_rcon_action(self, rcon_action):
        self.rcon_actions.append(rcon_action)
        if self.stat_container:
            self.stat_container.add_rcon_action(rcon_action)

    def set_has_flag(self, has_flag):
        self.has_flag = True
        if self.stat_container:
            self.stat_container.set_has_flag(has_flag)

    def add_flag_drop(self, flag_drop):
        self.flag_drops.append(flag_drop)
        if self.stat_container:
            self.stat_container.add_flag_drop(flag_drop)

    def add_flag_return(self):
        self.flag_returns += 1
        if self.stat_container:
            self.stat_container.add_flag_return()

    def add_flag_loss(self, flag_loss):
        self.flag_losses += 1
        if self.stat_container:
            self.stat_container.add_flag_loss(flag_loss)

    def add_flag_cap(self):
        self.flag_caps += 1
        if self.stat_container:
            self.stat_container.add_flag_cap()

