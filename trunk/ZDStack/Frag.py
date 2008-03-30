from ZDStack.Dictable import Dictable

class Frag(Dictable):

    def __init__(self, fragger, fraggee, weapon):
        self.fragger = fragger
        self.fraggee = fraggee
        self.weapon = weapon
        self.add_key('fragger', fragger)
        self.add_key('fraggee', fraggee)
        self.add_key('weapon', weapon)

