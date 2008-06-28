from decimal import Decimal

class Listable(list):

    """Class that recursively exports its contents."""

    def __init__(self, x=[]):
        """Initializes a Listable.

        x: an initial list

        """
        list.__init__(self, x)

    def exportables(self):
        """Returns a list of values to export."""
        return [x for x in self]

    def export(self):
        """Returns a list of recursively exported values."""
        out = []
        for x in self.exportables():
            if hasattr(x, 'export'):
                out.append(x.export())
            elif isinstance(x, Decimal):
                out.append(str(x))
            else:
                out.append(x)
        return out

