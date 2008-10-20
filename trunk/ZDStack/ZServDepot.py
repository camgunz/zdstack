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
from ZDStack.FakeZServ import FakeZServ
from ZDStack.FakeTeamDMZServ import FakeTeamDMZServ
from ZDStack.FakeCTFZServ import FakeCTFZServ

game_mode_dict = {'coop': (CoopZServ, GeneralZServStatsMixin),
                  'duel': (DuelZServ, GeneralZServStatsMixin),
                  'ffa': (FFAZServ, GeneralZServStatsMixin),
                  'teamdm': (TeamDMZServ, TeamZServStatsMixin),
                  'ctf': (CTFZServ, CTFTeamZServStatsMixin)}

def get_fake_zserv_class(game_mode, memory_slots, log_type):
    """Returns a Fake ZServclass.

    game_mode:    A string representing the game mode, valid options
                  are in game_mode_dict.keys().
    log_type:     The type of log to be parsed, either 'server' or
                  'client'.

    """
    if game_mode in ('coop', 'duel', 'ffa'):
        zs_class = FakeZServ
    elif game_mode == 'teamdm':
        zs_class = FakeTeamDMZServ
    elif game_mode == 'ctf':
        zs_class = FakeCTFZServ
    else:
        raise ValueError("Invalid game mode [%s]" % (game_mode))
    class StatsEnabledZServ(zs_class):
        def __init__(self):
            zs_class.__init__(self, log_type=log_type)
    return StatsEnabledZServ

def get_zserv_class(game_mode, memory_slots, log_ips=False, load_plugins=False):
    """Returns a ZServ class.

    game_mode:    a string representing the game mode, valid options
                  are in game_mode_dict.keys()
    memory_slots: an int representing the number of games to remember
    log_ips:      a boolean, whether or not to log IP addresses in the
                  Player => IP database
    load_plugins: a boolean, whether or not to load plugins


    """
    if game_mode not in game_mode_dict:
        raise ValueError("Invalid game mode [%s]" % (game_mode))
    zs_class, mixin_class = gmd[game_mode]
    s = "Got ZS [%s], MIXIN [%s] for game_mode [%s]"
    logging.getLogger('').info(s % (zs_class, mixin_class, game_mode))
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
            def __init__(self, name, config, zdstack):
                zs_class.__init__(self, name, config, zdstack)
                stats_mixin.__init__(self)
        return StatsEnabledZServ

