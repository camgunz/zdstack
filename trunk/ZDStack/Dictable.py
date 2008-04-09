class Dictable(dict):

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

    def export(self):
        out = {}
        for x, y in self.items():
            if hasattr(y, 'export'):
                out[x] = y.export()
            else:
                out[x] = y
        return out

