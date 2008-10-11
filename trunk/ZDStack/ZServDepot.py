import logging

from ZDStack.CTFZServ import CTFZServ
from ZDStack.TeamDMZServ import TeamDMZServ
from ZDStack.FFAZServ import FFAZServ
from ZDStack.DuelZServ import DuelZServ
from ZDStack.CoopZServ import CoopZServ
from ZDStack.TeamZServStatsMixin import TeamZServStatsMixin
from ZDStack.CTFTeamZServStatsMixin import CTFTeamZServStatsMixin
from ZDStack.GeneralZServStatsMixin import GeneralZServStatsMixin
from ZDStack.ConnectionZServStatsMixin import ConnectionZServStatsMixin as CZSM
from ZDStack.FakeCTFZServ import FakeCTFZServ
from ZDStack.FakeTeamDMZServ import FakeTeamDMZServ
from ZDStack.FakeFFAZServ import FakeFFAZServ
from ZDStack.FakeDuelZServ import FakeDuelZServ
from ZDStack.FakeCoopZServ import FakeCoopZServ
from ZDStack.TeamFakeZServStatsMixin import TeamFakeZServStatsMixin
from ZDStack.CTFTeamFakeZServStatsMixin import CTFTeamFakeZServStatsMixin
from ZDStack.GeneralFakeZServStatsMixin import GeneralFakeZServStatsMixin

game_mode_dict = {'coop': (CoopZServ, GeneralZServStatsMixin),
                  'duel': (DuelZServ, GeneralZServStatsMixin),
                  'ffa': (FFAZServ, GeneralZServStatsMixin),
                  'teamdm': (TeamDMZServ, TeamZServStatsMixin),
                  'ctf': (CTFZServ, CTFTeamZServStatsMixin)}

fake_game_mode_dict = {'coop': (FakeCoopZServ, GeneralFakeZServStatsMixin),
                       'duel': (FakeDuelZServ, GeneralFakeZServStatsMixin),
                       'ffa': (FakeFFAZServ, GeneralFakeZServStatsMixin),
                       'teamdm': (FakeTeamDMZServ, TeamFakeZServStatsMixin),
                       'ctf': (FakeCTFZServ, CTFTeamFakeZServStatsMixin)}

def get_zserv_class(game_mode, memory_slots, log_ips=False, load_plugins=False,
                    fake=False, log_type=False):
    """Returns a ZServ class.

    game_mode:    a string representing the game mode, valid options
                  are in game_mode_dict.keys()
    memory_slots: an int representing the number of games to remember
    log_ips:      a boolean, whether or not to log IP addresses in the
                  Player => IP database
    load_plugins: a boolean, whether or not to load plugins


    """
    if fake:
        if not log_type:
            es = "When requesting a FakeZServ class, a 'log_type' must be "
            es += "given."
            raise ValueError(es)
        gmd = fake_game_mode_dict
        log_ips = False
        load_plugins = False
    else:
        gmd = game_mode_dict
    if game_mode not in gmd:
        raise ValueError("Invalid game mode [%s]" % (game_mode))
    zs_class, mixin_class = gmd[game_mode]
    s = "Got ZS [%s], MIXIN [%s] for game_mode [%s]"
    logging.getLogger('').info(s % (zs_class, mixin_class, game_mode))
    if fake:
        class stats_mixin(mixin_class):
            def __init__(self):
                mixin_class.__init__(self, memory_slots, log_type=log_type)
    else:
        class stats_mixin(mixin_class):
            def __init__(self):
                mixin_class.__init__(self, memory_slots,
                                           load_plugins=load_plugins)
    if log_ips:
        class StatsAndIPEnabledZServ(zs_class, stats_mixin, CZSM):
            def __init__(self, name, config, zdstack):
                zs_class.__init__(self, name, config, zdstack)
                stats_mixin.__init__(self)
                CZSM.__init__(self)
        return StatsAndIPEnabledZServ
    else:
        class StatsEnabledZServ(zs_class, stats_mixin):
            if fake:
                def __init__(self, name):
                    zs_class.__init__(self, name)
                    stats_mixin.__init__(self)
            else:
                def __init__(self, name, config, zdstack):
                    zs_class.__init__(self, name, config, zdstack)
                    stats_mixin.__init__(self)
        return StatsEnabledZServ

