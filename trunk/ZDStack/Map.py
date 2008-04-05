from datetime import datetime, timedelta
from ZDStack.BaseStatKeeper import BaseStatKeeper

class Map(BaseStatKeeper):

    def __init__(self, number, name):
        self.number = number
        self.name = name
        self.start_time = datetime.now()
        BaseStatKeeper.__init__(self)

    def set_has_flag(self, has_flag):
        pass

