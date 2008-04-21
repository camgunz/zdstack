from ZDStack.BaseTeam import BaseTeam
from ZDStack.CTFStatKeeper import CTFStatKeeper

class CTFTeam(BaseTeam, CTFStatKeeper):

    def __init__(self, color):
        BaseTeam.__init__(self, color)
        CTFStatKeeper.__init__(self)

    def initialize(self):
        BaseTeam.initialize(self)
        CTFStatKeeper.initialize(self)

