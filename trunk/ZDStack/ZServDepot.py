from ZDStack import log
from ZDStack.CTFZServ import CTFZServ
from ZDStack.TeamDMZServ import TeamDMZServ
from ZDStack.FFAZServ import FFAZServ
from ZDStack.DuelZServ import DuelZServ
from ZDStack.CoopZServ import CoopZServ
from ZDStack.TeamZServStatsMixin import TeamZServStatsMixin
from ZDStack.CTFTeamZServStatsMixin import CTFTeamZServStatsMixin
from ZDStack.GeneralZServStatsMixin import GeneralZServStatsMixin
from ZDStack.ConnectionZServStatsMixin import ConnectionZServStatsMixin as CZSM

game_mode_dict = {'coop': (CoopZServ, GeneralZServStatsMixin),
                  'duel': (DuelZServ, GeneralZServStatsMixin),
                  'ffa': (FFAZServ, GeneralZServStatsMixin),
                  'teamdm': (TeamDMZServ, TeamZServStatsMixin),
                  'ctf': (CTFZServ, CTFTeamZServStatsMixin)}

def get_zserv_class(game_mode, memory_slots, enable_stats=False, log_ips=False):
    if game_mode not in game_mode_dict:
        raise ValueError("Invalid game mode [%s]" % (game_mode))
    zs_class, mixin_class = game_mode_dict[game_mode]
    s = "Got ZS [%s], MIXIN [%s] for game_mode [%s]"
    log(s % (zs_class, mixin_class, game_mode))
    class stats_mixin(mixin_class):
        def __init__(self):
            mixin_class.__init__(self, memory_slots)
    if enable_stats:
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
    elif log_ips:
            class IPEnabledZServ(zs_class, stats_mixin):
                def __init__(self, name, config, zdstack):
                    zs_class.__init__(self, name, config, zdstack)
                    CZSM.__init__(self)
            return IPEnabledZServ
    else:
        class PlainZServ(zs_class):
            def __init__(self, name, config, zdstack):
                zs_class.__init__(self, name, config, zdstack)
        return PlainZServ

