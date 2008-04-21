from datetime import datetime
from ZDStack.BaseStatKeeper import BaseStatKeeper

class BaseMap(BaseStatKeeper):

    def __init__(self, number, name):
        BaseStatKeeper.__init__(self)
        self.number = number
        self.name = name
        self.start_time = datetime.now()

    def __eq__(self, x):
        return type(x) == type(self) and \
               x.number == self.number and \
               x.name == self.name and \
               x.start_time == self.start_time

    def __lt__(self, x):
        return type(x) == type(self) and \
               x.number == self.number and \
               x.name == self.name and \
               x.start_time > self.start_time

    def __gt__(self, x):
        return type(x) == type(self) and \
               x.number == self.number and \
               x.name == self.name and \
               x.start_time < self.start_time

    def set_has_flag(self, has_flag):
        pass

