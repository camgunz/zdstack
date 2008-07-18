
__all__ = ['process_frags', 'get_player_totals', 'extract_frags', 'get_totals']

def uniqify(x):
    s = set()
    return [y for y in x if y not in s and not s.add(y)]

def get_ratio(n, d):
    t = '%1.1f%%'
    if d < 1:
        if n < 1:
            r = t % 0
        else:
            r = 'inf'
    else:
        r = t % ((float(n) / float(d)) * 100.0)
    return r

def get_player_totals(player):
    player['flag_ratio'] = None
    player['pick_ratio'] = None
    player['return_ratio'] = None
    if 'flag_caps' in player and 'flag_touches' in player:
        player['flag_ratio'] = get_ratio(player['flag_caps'],
                                         player['flag_touches'])
    if 'flag_picks' in player:
        player['pick_ratio'] = get_ratio(player['flag_picks'],
                                         player['total_flag_losses'])
    if 'flag_returns' in player:
        player['return_ratio'] = get_ratio(player['flag_returns'],
                                           player['total_flag_drops'])
    return player

def get_totals(stats):
    """
    for stat in ('frags', 'deaths'):
        if stat in stats:
            stats['total_' + stat] = len(stats[stat])
            # stats[stat] = extract_frags(stats[stat])
        else:
            stats['total_' + stat] = 0
            # stats[stat] = {}
    """
    stats['frag_ratio'] = None
    stats['flag_ratio'] = None
    stats['pick_ratio'] = None
    stats['return_ratio'] = None
    if 'total_frags' in stats and 'total_deaths' in stats:
        stats['frag_ratio'] = get_ratio(stats['total_frags'],
                                        stats['total_deaths'])
    if 'flag_caps' in stats and 'flag_touches' in stats:
        stats['flag_ratio'] = get_ratio(stats['flag_caps'],
                                        stats['flag_touches'])
    if 'flag_picks' in stats and 'total_flag_losses' in stats:
        stats['pick_ratio'] = get_ratio(stats['flag_picks'],
                                        stats['total_flag_losses'])
    if 'flag_returns' in stats and 'total_flag_drops' in stats:
        stats['return_ratio'] = get_ratio(stats['flag_returns'],
                                          stats['total_flag_drops'])
    return stats

