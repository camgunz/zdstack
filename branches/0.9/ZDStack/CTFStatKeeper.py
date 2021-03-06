from ZDStack import debug
from ZDStack.Listable import Listable
from ZDStack.TeamStatKeeper import TeamStatKeeper

class CTFStatKeeper(TeamStatKeeper):

    def __init__(self):
        TeamStatKeeper.__init__(self)

    def initialize(self):
        TeamStatKeeper.initialize(self)
        self.flag_drops = Listable()
        self.flag_losses = Listable()
        self.flag_touches = 0
        self.flag_returns = 0
        self.flag_picks = 0
        self.flag_caps = 0
        self.has_flag = False

    def set_has_flag(self, has_flag):
        debug()
        self.has_flag = has_flag
        if self.stat_container:
            self.stat_container.set_has_flag(has_flag)

    def add_flag_touch(self):
        debug()
        self.flag_touches += 1
        if self.stat_container:
            self.stat_container.add_flag_touch()
        self.set_has_flag(True)

    def add_flag_drop(self, flag_drop):
        debug()
        self.flag_drops.append(flag_drop)
        if self.stat_container:
            self.stat_container.add_flag_drop(flag_drop)
        self.set_has_flag(False)

    def add_flag_pick(self):
        debug()
        self.flag_picks += 1
        if self.stat_container:
            self.stat_container.add_flag_pick()
        self.set_has_flag(True)

    def add_flag_return(self):
        debug()
        self.flag_returns += 1
        if self.stat_container:
            self.stat_container.add_flag_return()

    def add_flag_loss(self, flag_loss):
        debug()
        self.flag_losses.append(flag_loss)
        if self.stat_container:
            self.stat_container.add_flag_loss(flag_loss)
        self.set_has_flag(False)

    def add_flag_cap(self):
        debug()
        self.flag_caps += 1
        if self.stat_container:
            self.stat_container.add_flag_cap()
        self.set_has_flag(False)

