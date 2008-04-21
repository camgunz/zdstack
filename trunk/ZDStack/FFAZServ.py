from ZDStack.DMZServ import DMZServ

class FFAZServ(DMZServ):

    def __init__(self, name, config, zdstack):
        DMZServ.__init__(self, name, 'ffa', config, zdstack)

