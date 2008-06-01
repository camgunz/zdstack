import pprint
import urllib
from operator import itemgetter

import web

from ZDStats import get_server
from ZDStats import StatTransform

from pyfileutils import append_file

SERVER = get_server()

__all__ = ['ZServNotFoundError', 'nice_gamemode', 'get_zserv',
           'get_all_zservs', 'get_stats', 'get_valid_teams',
           'strip_invalid_teams', 'strip_invalid_players',
           'compute_map_totals', 'compute_team_totals',
           'compute_player_totals']

_ALL_TEAMS = ('red', 'blue', 'white', 'green')

class _NotFoundError(Exception):
    def __init__(self, thing, thing_name):
        Exception.__init__(self, "%s [%s] not found" % (thing, thing_name))

class ZServNotFoundError(_NotFoundError):
    def __init___(self, zserv_name):
        _NotFoundError.__init__(self, 'ZServ', zserv_name)

class ZServStatsLimit(Exception):
    def __init__(self, zserv_name, i):
        es = "ZServ [%s] does not have %d slots for stats"
        Exception.__init__(self, es % (zserv_name, i))

nice_gamemode = {'coop': 'Coop', 'ctf': 'CTF',
                 'duel': 'Duel', 'ffa': 'FFA',
                 'teamdm': 'TeamDM'}

def _log(s):
    append_file('===\n%s\n===\n' % (s), 'zdstats.log', overwrite=True)

def _log_data(description, data):
    _log('%s:\n%s' % (description, pprint.pformat(data)))

def ellipsize(x, max_length=30):
    if len(x) > max_length:
        return x[:max_length] + '...'
    else:
        return x

def _transform_zserv(zserv):
    zserv['html_hostname'] = web.htmlquote(zserv['hostname'])
    zserv['url_name'] = urllib.quote(zserv['name'])
    zserv['html_name'] = web.htmlquote(zserv['name'])
    zserv['nice_type'] = nice_gamemode[zserv['type']]
    zserv['nice_wads'] = []
    for wad in zserv['wads']:
        if wad in zserv['optional_wads']:
            zserv['nice_wads'].append(wad.join(['[', ']']))
        else:
            zserv['nice_wads'].append(wad)
    zserv['joined_wads'] = ', '.join(zserv['nice_wads'])
    zserv['joined_optional_wads'] = ', '.join(zserv['optional_wads'])
    zserv['joined_maps'] = ', '.join(zserv['maps'])
    zserv['nice_type'] = nice_gamemode[zserv['type']]
    if 'map' in zserv and zserv['map']:
        if 'name' in zserv['map']:
            zserv['map']['name'] = ellipsize(zserv['map']['name'])
        if 'number' in zserv['map']:
            zserv['map']['number'] = str(zserv['map']['number']).zfill(2)
    if 'remembered_stats' in zserv:
        for m in zserv['remembered_stats']:
            m['name'] = ellipsize(m['name'])
    return zserv

def get_zserv(zserv_name):
    try:
        zserv = SERVER.get_zserv(zserv_name)
    except:
        raise ZServNotFoundError(zserv_name)
    # _log_data('ZServ', zserv)
    return _transform_zserv(zserv)

def get_all_zservs():
    zservs = SERVER.get_all_zservs()
    zservs.sort(key=itemgetter('port'))
    return [_transform_zserv(x) for x in zservs]

def get_valid_teams(zserv):
    if not 'max_teams' in zserv or not zserv['max_teams']:
        return ()
    elif zserv['max_teams'] == 4:
        return ('red', 'blue', 'green', 'white')
    elif zserv['max_teams'] == 3:
        return ('red', 'blue', 'green')
    elif zserv['max_teams'] == 2:
        return ('red', 'blue')
    
def strip_invalid_teams(stats, valid_teams):
    if not valid_teams:
        stats['teams'] = []
    if not 'teams' in stats or not stats['teams']:
        stats['teams'] = []
    else:
        stats['teams'] = [stats['teams'][x] for x in valid_teams]
    return stats

def strip_invalid_players(stats, valid_teams):
    if not 'players' in stats or not stats['players']:
        stats['players'] = []
    elif not valid_teams:
        stats['players'] = stats['players'].values()
    else:
        stats['players'] = [x for x in stats['players'].values() \
                                if 'color' in x and x['color'] in valid_teams]
    return stats

def compute_map_totals(map_stats):
    return StatTransform.get_totals(map_stats)

def compute_team_totals(team_stats):
    return [StatTransform.get_totals(x) for x in team_stats]

def compute_player_totals(player_stats):
    out = []
    for player_stat in player_stats:
        out.append(StatTransform.get_player_totals(player_stat))
    return out

def get_stats(zserv, back=0):
    if back == 0:
        try:
            current_map = SERVER.get_current_map(zserv['name'])
            all_players = SERVER.get_all_players(zserv['name'])
            stats = {}
            stats['map'] = current_map
            stats['players'] = all_players
            if zserv['type'] in ('ctf', 'teamdm'):
                all_teams = SERVER.get_all_teams(zserv['name'])
                stats['teams'] = all_teams
        except:
            raise # for debugging
            raise ZServNotFoundError(zserv['name'])
    else:
        try:
            stats = SERVER.get_remembered_stats(zserv['name'], back)
        except Exception, e:
            es = str(e)
            if es.endswith(' not found">') \
              and 'ZServ' in es \
              and 'ValueError' in es:
                raise ZServNotFoundError(zserv['name'])
            elif es.endswith("""ons.IndexError'>:list index out of range">"""):
                raise ZServStatsLimit(zserv['name'], back)
            else:
                raise
    if zserv['type'] in ('ctf', 'teamdm'):
        valid_teams = get_valid_teams(zserv)
        # stats = strip_invalid_teams(stats, valid_teams)
        # stats = strip_invalid_players(stats, valid_teams)
        stats = strip_invalid_teams(stats, valid_teams)
        stats = strip_invalid_players(stats, None)
        stats['teams'] = compute_team_totals(stats['teams'])
    else:
        stats['players'] = stats['players'].values()
    stats['map'] = compute_map_totals(stats['map'])
    if 'name' in stats['map']:
        if len(stats['map']['name']) > 30:
            zserv['map']['name'] = ellipsize(zserv['map']['name'])
    deaths = []
    flag_losses = []
    for player in stats['players']:
        deaths.extend(player['deaths'])
        if zserv['type'] == 'ctf':
            flag_losses.extend(player['flag_losses'])
        del player['frags']
        del player['deaths']
        if 'flag_drops' in player:
            del player['flag_drops']
        if 'flag_losses' in player:
            del player['flag_losses']
    processed_deaths = StatTransform.process_frags(deaths)
    processed_flag_losses = StatTransform.process_frags(flag_losses)
    for player in stats['players']:
        if player['name'] in processed_deaths:
            normal_frag_stats = processed_deaths[player['name']]
        else:
            normal_frag_stats = {'frags': 0, 'deaths': 0, 'ratio': '0.000',
                                 'weapons': {}, 'adversaries': {}}
        player['frag_stats'] = normal_frag_stats
        
        if player['name'] in processed_flag_losses:
            flag_frag_stats = processed_flag_losses[player['name']]
        else:
            flag_frag_stats = {'frags': 0, 'deaths': 0, 'ratio': '0.000'}
            flag_frag_stats = {'frags': 0, 'deaths': 0, 'ratio': '0.000',
                               'weapons': {}, 'adversaries': {}}
        player['flag_frag_stats'] = flag_frag_stats
    stats['players'] = dict([(x['name'], x) \
                            for x in compute_player_totals(stats['players'])])
    # _log_data('Map', stats['map'])
    # if 'teams' in stats:
        # _log_data('Teams', stats['teams'])
    # _log_data('Players', stats['players'])
    return stats

