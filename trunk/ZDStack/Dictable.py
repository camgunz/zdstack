from ZDStack.Listable import Listable

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

    def get_dict(self):
        out = {}
        for x, y in self.items():
            if isinstance(y, Dictable):
                out[x] = y.get_dict()
            if isinstance(y, Listable):
                out[x] = y.get_list()
            else:
                out[x] = y
        return out

