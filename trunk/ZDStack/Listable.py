class Listable(list):

    def get_list(self):
        out = []
        for x in self:
            if hasattr(x, 'export'):
                out.append(x.export())
            else:
                out.append(x)
        return out

