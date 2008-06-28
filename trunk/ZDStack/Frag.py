from ZDStack.Dictable import Dictable

class Frag(Dictable):

    """Frag represents a frag."""

    def __init__(self, fragger, fraggee, weapon, fragged_runner=False):
        """Initializes a Frag instance.

        fragger: a string representing the name of the fragger
        fraggee: a string representing the name of the fraggee
        weapon:  a string representing the name of the weapon
        fragged_runner: a boolean, whether or not the fraggee was a
                        flag carrier or not
        """
        self.fragger = fragger
        self.fraggee = fraggee
        self.weapon = weapon
        self.fragged_runner = fragged_runner

