from ZDStack.Listable import Listable

class Dictable(dict):

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

