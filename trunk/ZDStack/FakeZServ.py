from ZDStack.Dictable import Dictable

class FakeZServ:

    def __init__(self):
        """Initializes a BaseZServ instance.

        name:    a string representing the name of this ZServ.
        type:    the game-mode of this ZServ, like 'ctf', 'ffa', etc.
        config:  a dict of configuration values for this ZServ.
        zdstack: the calling ZDStack instance

        """
        self.pre_spawn_funcs = []
        self.post_spawn_funcs = []
        self.extra_exportables_funcs = []
        self.run_pre_spawn_funcs()

    def run_pre_spawn_funcs(self):
        for func, args, kwargs in self.pre_spawn_funcs:
            func(*args, **kwargs)

    def run_post_spawn_funcs(self):
        for func, args, kwargs in self.post_spawn_funcs:
            func(*args, **kwargs)

    def export(self):
        d = {}
        for func, args, kwargs in self.extra_exportables_funcs:
            d = func(*([d] + args), **kwargs)
        return Dictable(d).export()

