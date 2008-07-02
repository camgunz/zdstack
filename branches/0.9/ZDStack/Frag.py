from ZDStack.Dictable import Dictable

class Frag(Dictable):

    def __init__(self, fragger, fraggee, weapon):
        self.fragger = fragger
        self.fraggee = fraggee
        self.weapon = weapon

