from decimal import Decimal

from ZDStack import log

class Dictable(dict):

    def __init__(self, d={}):
        dict.__init__(self, d)

    def __getattr__(self, key): 
        try:
            return self[key]
        except KeyError, e:
            raise AttributeError, e

    def __setattr__(self, key, value): 
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, e:
            raise AttributeError, e

    def exportables(self):
        # log("Dictable: exportables")
        return [x for x in self.items()]

    def export(self):
        # log("Dictable: export")
        out = {}
        for x, y in self.exportables():
            if hasattr(y, 'export'):
                out[x] = y.export()
            elif isinstance(y, Decimal):
                out[x] = str(y)
            else:
                out[x] = y
        return out

