from ZDStack.Dictable import Dictable

class Listable(list):

    def get_list(self):
        out = []
        for x in self.list:
            if isinstance(x, Listable):
                out.append(x.get_list())
            elif isinstance(x, Dictable):
                out.append(x.get_dict())
            else:
                out.append(x)
        return out
