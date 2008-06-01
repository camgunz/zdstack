
import pprint
from pyfileutils import append_file

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

def _log(s):
    append_file('===\n%s\n===\n' % (s), 'stattransform.log', overwrite=True)

def _log_data(description, data):
    _log('%s:\n%s' % (description, pprint.pformat(data)))

class Player:
    def __init__(self, name):
        self.name = name
        self.adversaries = set()
        self.weapons = set()
        self.total_frags = 0
        self.total_deaths = 0
        self.player_frags = {}
        self.weapon_frags = {}
        self.player_weapon_frags = {}
        self.player_deaths = {}
        self.weapon_deaths = {}
        self.player_weapon_deaths = {}

    def add_adversary(self, adversary):
        self.adversaries.add(adversary)
        for a in self.adversaries:
            if a not in self.player_frags:
                self.player_frags[a] = 0
            if a not in self.player_deaths:
                self.player_deaths[a] = 0
            if a not in self.player_weapon_frags:
                self.player_weapon_frags[a] = {}.fromkeys(self.weapons, 0)
            if a not in self.player_weapon_deaths:
                self.player_weapon_deaths[a] = {}.fromkeys(self.weapons, 0)

    def add_weapon(self, weapon):
        self.weapons.add(weapon)
        for weapon in self.weapons:
            if weapon not in self.weapon_frags:
                self.weapon_frags[weapon] = 0
            if weapon not in self.weapon_deaths:
                self.weapon_deaths[weapon] = 0
            for player in self.player_weapon_frags:
                if weapon not in self.player_weapon_frags[player]:
                    self.player_weapon_frags[player][weapon] = 0
            for player in self.player_weapon_deaths:
                if weapon not in self.player_weapon_deaths[player]:
                    self.player_weapon_deaths[player][weapon] = 0

    def add_frag(self, fraggee, weapon):
        self.total_frags += 1
        if not weapon in self.weapons:
            self.add_weapon(weapon)
        if not fraggee in self.adversaries:
            self.add_adversary(fraggee)
        self.weapon_frags[weapon] += 1
        self.player_frags[fraggee] += 1
        self.player_weapon_frags[fraggee][weapon] += 1

    def add_death(self, fragger, weapon):
        self.total_deaths += 1
        if not weapon in self.weapons:
            self.add_weapon(weapon)
        if not fragger in self.adversaries:
            self.add_adversary(fragger)
        self.weapon_deaths[weapon] += 1
        self.player_deaths[fragger] += 1
        self.player_weapon_deaths[fragger][weapon] += 1

    def get_dict(self):
        d = {'adversaries': {}.fromkeys(self.adversaries),
             'weapons': {}.fromkeys(self.weapons),
             'frags': self.total_frags,
             'deaths': self.total_deaths,
             'ratio': get_ratio(self.total_frags, self.total_deaths)}
        for a in d['adversaries']:
            d['adversaries'][a] = {'frags': self.player_frags[a],
                                   'deaths': self.player_deaths[a],
                                   'ratio': get_ratio(self.player_frags[a],
                                                      self.player_deaths[a])}
        for weapon in d['weapons']:
            d['weapons'][weapon] = \
                                {'frags': self.weapon_frags[weapon],
                                 'deaths': self.weapon_deaths[weapon],
                                 'ratio': get_ratio(self.weapon_frags[weapon],
                                                    self.weapon_deaths[weapon])}
            for adversary in d['adversaries']:
                if weapon not in d['adversaries'][adversary]:
                    d['adversaries'][adversary][weapon] = {}
                    total_frags = self.player_weapon_frags[adversary][weapon]
                    total_deaths = self.player_weapon_deaths[adversary][weapon]
                    ratio = get_ratio(total_frags, total_deaths)
                    d['adversaries'][adversary][weapon]['frags'] = total_frags
                    d['adversaries'][adversary][weapon]['deaths'] = total_deaths
                    d['adversaries'][adversary][weapon]['ratio'] = ratio
        return d

def process_frags(frags):
    players = {}
    for frag in frags:
        if frag['fragger'] not in players:
            players[frag['fragger']] = Player(frag['fragger'])
        if frag['fraggee'] not in players:
            players[frag['fraggee']] = Player(frag['fraggee'])
        
    for frag in frags:
        weapon, fragger, fraggee = (frag['weapon'], frag['fragger'],
                                    frag['fraggee'])
        if fragger != fraggee: # no suicides!
            players[fragger].add_frag(fraggee, weapon)
        players[fraggee].add_death(fragger, weapon)
    out = dict([(x.name, x.get_dict()) for x in players.values()])
    return out

def get_player_totals(player):
    player['flag_ratio'] = None
    player['pick_ratio'] = None
    player['return_ratio'] = None
    if 'flag_caps' in player and 'flag_touches' in player:
        player['flag_ratio'] = get_ratio(player['flag_caps'],
                                         player['flag_touches'])
    if 'flag_picks' in player and 'deaths' in player['flag_frag_stats']:
        player['pick_ratio'] = get_ratio(player['flag_picks'],
                                         player['flag_frag_stats']['deaths'])
    if 'flag_returns' in player and 'frags' in player['flag_frag_stats']:
        player['return_ratio'] = get_ratio(player['flag_returns'],
                                           player['flag_frag_stats']['frags'])
    return player

def get_totals(stats):
    for stat in ('frags', 'deaths', 'flag_losses', 'flag_drops'):
        if stat in stats:
            stats['total_' + stat] = len(stats[stat])
            stats[stat] = extract_frags(stats[stat])
        else:
            stats['total_' + stat] = 0
            stats[stat] = {}
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

def extract_frags(frags):
    out = {'weapons': {}, 'players': {}}
    ###
    # Ladna:
    #     Frags with Super Shotgun: 77
    #         On Nostar:            16
    #     Deaths by Super Shotgun:  70
    #         By Nostar:            18
    #     Flag Drops with Super Shotgun:  13
    #         On Nostar:                   1
    #     Flag Losses by Super Shotgun:    8
    #         By Nostar:                   7
    #
    # out['players']['Nostar']
    # out['players']['Ladna']
    # out['players']['Nostar']['total_frags']
    # out['players']['Nostar']['total_deaths']
    # out['players']['Nostar']['Super Shotgun']
    # out['players']['Nostar']['Rocket Launcher']
    # out['players']['Nostar']['Super Shotgun']['total_frags']
    # out['players']['Nostar']['Super Shotgun']['total_deaths']
    # out['players']['Nostar']['Super Shotgun']['frags']
    # out['players']['Nostar']['Super Shotgun']['deaths']
    # out['players']['Nostar']['Super Shotgun']['frags']['Ladna']
    # out['players']['Nostar']['Super Shotgun']['deaths']['Ladna']
    #
    ###
    for frag in frags:
        weapon, fragger, fraggee = (frag['weapon'], frag['fragger'],
                                    frag['fraggee'])
        if weapon not in out['weapons']:
            out['weapons'][weapon] = 1
        else:
            out['weapons'][weapon] += 1
        if fragger not in out['players']:
            out['players'][fragger] = \
                {weapon: {'frags': {fraggee: 1}, 'total_frags': 1,
                          'deaths': {fraggee: 0}, 'total_deaths': 0},
                          'total_frags': 1, 'total_deaths': 0}
        elif weapon not in out['players'][fragger]:
            out['players'][fragger][weapon] = \
                {'frags': {fraggee: 1}, 'total_frags': 1,
                 'deaths': {fraggee: 0}, 'total_deaths': 0}
            out['players'][fragger]['total_frags'] += 1
        elif fraggee not in out['players'][fragger][weapon]['frags']:
            out['players'][fragger][weapon]['frags'] = {fraggee: 1}
            out['players'][fragger][weapon]['total_frags'] += 1
            out['players'][fragger]['total_frags'] += 1
        else:
            out['players'][fragger][weapon]['frags'][fraggee] += 1
            out['players'][fragger][weapon]['total_frags'] += 1
            out['players'][fragger]['total_frags'] += 1
        if fraggee not in out['players']:
            out['players'][fraggee] = \
                {weapon: {'frags': {fragger: 0}, 'total_frags': 0,
                          'deaths': {fragger: 1}, 'total_deaths': 1},
                          'total_frags': 0, 'total_deaths': 1}
        elif weapon not in out['players'][fraggee]:
            out['players'][fraggee][weapon] = \
                {'frags': {fragger: 0}, 'total_frags': 0,
                 'deaths': {fragger: 1}, 'total_deaths': 1}
            out['players'][fraggee]['total_deaths'] += 1
        elif fraggee not in out['players'][fraggee][weapon]['deaths']:
            out['players'][fraggee][weapon]['deaths'] = {fragger: 1}
            out['players'][fraggee][weapon]['total_deaths'] += 1
            out['players'][fraggee]['total_deaths'] += 1
        else:
            out['players'][fraggee][weapon]['deaths'][fragger] += 1
            out['players'][fraggee][weapon]['total_deaths'] += 1
            out['players'][fraggee]['total_deaths'] += 1
    for player in out['players']:
        if 'total_frags' not in out['players'][player]:
            out['players'][player]['total_frags'] = 0
        if 'total_deaths' not in out['players'][player]:
            out['players'][player]['total_deaths'] = 0
        ratio = get_ratio(out['players'][player]['total_frags'],
                          out['players'][player]['total_deaths'])
        out['players'][player]['ratio'] = ratio
        for weapon in out['players'][player]:
            if weapon in ('total_frags', 'total_deaths', 'ratio'):
                continue
            if 'total_frags' not in out['players'][player][weapon]:
                out['players'][player][weapon]['total_frags'] = 0
            if 'total_deaths' not in out['players'][player][weapon]:
                out['players'][player][weapon]['total_deaths'] = 0
            ratio = get_ratio(out['players'][player][weapon]['total_frags'],
                              out['players'][player][weapon]['total_deaths'])
            out['players'][player][weapon]['ratio'] = ratio
    return out

