from ZDStack.Dictable import Dictable

class FakeZServ:

    """FakeZServ is a FakeZServ for client log parsing."""

    def __init__(self):
        """Initializes a FakeZServ instance."""
        self.pre_spawn_funcs = []
        self.post_spawn_funcs = []
        self.extra_exportables_funcs = []
        self.run_pre_spawn_funcs()

    def run_pre_spawn_funcs(self):
        """Runs pre_spawn_funcs."""
        for func, args, kwargs in self.pre_spawn_funcs:
            func(*args, **kwargs)

    def run_post_spawn_funcs(self):
        """Runs post_spawn_funcs."""
        for func, args, kwargs in self.post_spawn_funcs:
            func(*args, **kwargs)

    def export(self):
        """Exports ZServ attributes."""
        d = {}
        for func, args, kwargs in self.extra_exportables_funcs:
            d = func(*([d] + args), **kwargs)
        return Dictable(d).export()

