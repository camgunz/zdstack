from ZDStack.Listable import Listable
from ZDStack.BasePlayer import BasePlayer

class CTFPlayer(BasePlayer):

    def __init__(self, name, zserv, ip=None):
        BasePlayer.__init__(self, name, zserv, ip)
        self.team = None
        if self.team is not None:
            self.color = self.team.color
        else:
            self.stat_container = self.map
            self.color = None

    def initialize(self):
        BasePlayer.initialize(self)
        self.flag_drops = Listable()
        self.flag_losses = Listable()
        self.flag_touches = 0
        self.flag_returns = 0
        self.flag_picks = 0
        self.flag_caps = 0
        self.has_flag = False

    def set_map(self, map):
        self.map = map

    def set_team(self, team):
        self.team = team
        if self.team is not None:
            self.color = self.team.color
        else:
            self.color = None
        self.stat_container = self.team

    def set_has_flag(self, has_flag):
        self.has_flag = has_flag
        if self.stat_container:
            self.stat_container.set_has_flag(has_flag)

    def add_flag_touch(self):
        self.flag_touches += 1
        if self.stat_container:
            self.stat_container.add_flag_touch()
        self.set_has_flag(True)

    def add_flag_drop(self, flag_drop):
        self.flag_drops.append(flag_drop)
        if self.stat_container:
            self.stat_container.add_flag_drop(flag_drop)
        self.set_has_flag(False)

    def add_flag_pick(self):
        self.flag_picks += 1
        if self.stat_container:
            self.stat_container.add_flag_pick()
        self.set_has_flag(True)

    def add_flag_return(self):
        self.flag_returns += 1
        if self.stat_container:
            self.stat_container.add_flag_return()

    def add_flag_loss(self, flag_loss):
        self.flag_losses.append(flag_loss)
        if self.stat_container:
            self.stat_container.add_flag_loss(flag_loss)
        self.set_has_flag(False)

    def add_flag_cap(self):
        self.flag_caps += 1
        if self.stat_container:
            self.stat_container.add_flag_cap()
        self.set_has_flag(False)

