from ZDStack.Dictable import Dictable

class Frag(Dictable):

    def __init__(self, fragger, fraggee, weapon, fragged_runner=False):
        self.fragger = fragger
        self.fraggee = fraggee
        self.weapon = weapon
        self.fragged_runner = fragged_runner

