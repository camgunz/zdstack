from datetime import datetime
from ZDStack.BaseStatKeeper import BaseStatKeeper

class BaseMap(BaseStatKeeper):

    """Base Map class, holds stats for a map."""

    def __init__(self, number, name):
        """Initializes BaseMap

        number: an integer representing the number of the map
        name:   a string representing the name of the map

        """
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
        """Normally this toggles the 'has_flag' flag, but not for maps."""
        pass

