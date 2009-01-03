import logging

from decimal import Decimal

class Dictable(dict):

    """Dictable is a class that exports its attributes as a dict."""

    def __init__(self, d={}):
        """Initializes a Dictable."""
        dict.__init__(self, d)

    def __getattr__(self, key): 
        try:
            return self[key]
        except KeyError, e:
            logging.debug("Items: %s" % (self.items()))
            raise AttributeError, e

    def __setattr__(self, key, value): 
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, e:
            raise AttributeError, e

    def exportables(self):
        """Returns a list of strings representing the names of exportable attributes."""
        return [x for x in self.items()]

    def export(self):
        """Exports a dict of this class's attributes and values."""
        out = {}
        for x, y in self.exportables():
            if hasattr(y, 'export'):
                out[x] = y.export()
            elif isinstance(y, Decimal):
                out[x] = str(y)
            else:
                out[x] = y
        return out

