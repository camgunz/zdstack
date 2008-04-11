class Listable(list):

    def __init__(self, x=[]):
        list.__init__(self, x)

    def exportables(self):
        return [x for x in self]

    def export(self):
        out = []
        for x in self.exportables():
            if hasattr(x, 'export'):
                out.append(x.export())
            else:
                out.append(x)
        return out

