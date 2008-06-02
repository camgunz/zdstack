import logging

from ZDStack.BaseZServ import BaseZServ

class DMZServ(BaseZServ):

    def __init__(self, name, type, config, zdstack):
        self.deathmatch = True
        BaseZServ.__init__(self, name, type, config, zdstack)

    def load_config(self, config):
        logging.getLogger('').info('')
        def is_valid(x):
            return x in config and config[x]
        BaseZServ.load_config(self, config)
        if is_valid('fraglimit'):
            self.fraglimit = int(self.config['fraglimit'])
        elif is_valid(self.type + '_fraglimit'):
            self.fraglimit = int(self.config[self.type + '_fraglimit'])
        self.config['fraglimit'] = self.fraglimit

    def get_configuration(self):
        logging.getLogger('').info('')
        return BaseZServ.get_configuration(self) + 'set deathmatch "1"\n'

