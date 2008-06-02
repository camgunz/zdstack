import csv
import logging

from base64 import b64encode

from ZDStack.Utils import parse_player_name, homogenize, html_escape, get_ratio
from ZDStack.Listable import Listable
from ZDStack.PlayerDB import save_player_ip, get_possible_aliases
from ZDStack.BaseStatKeeper import BaseStatKeeper


class BasePlayer(BaseStatKeeper):

    def __init__(self, name, zserv, ip=None):
        logging.getLogger('').debug('name: [%s]' % (name))
        BaseStatKeeper.__init__(self)
        self.name = name
        self.zserv = zserv
        self.ip = ip
        self.tag, self.player_name = parse_player_name(self.name)
        self.homogenized_name = homogenize(self.name)
        self.escaped_name = html_escape(self.name)
        self.escaped_homogenized_name = html_escape(homogenize(self.name))
        self.encoded_name = b64encode(self.name)
        self.homogenized_player_name = homogenize(self.player_name)
        self.escaped_player_name = html_escape(self.player_name)
        self.escaped_homogenized_player_name = \
                                    html_escape(homogenize(self.player_name))
        if self.tag is None:
            self.homogenized_tag = None
            self.escaped_tag = None
            self.escaped_homogenized_tag = None
        else:
            self.homogenized_tag = homogenize(self.tag)
            self.escaped_tag = html_escape(self.tag)
            self.escaped_homogenized_tag = html_escape(homogenize(self.tag))
        self.set_map(self.zserv.map)
        self.stat_container = self.zserv.map
        self.playing = False
        self.disconnected = False
        if self.ip:
            save_player_ip(self.name, self.ip)
        self.initialize()
        ###
        # TODO:
        #   - Add latency/packet-loss tracking
        ###

    def initialize(self):
        logging.getLogger('').debug('')
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
        self.rcon_actions = Listable()
        self.rcon_denials = 0
        self.rcon_accesses = 0

    def add_adversary(self, adversary):
        logging.getLogger('').debug('')
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
        logging.getLogger('').debug('')
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

    def add_frag(self, frag):
        logging.getLogger('').debug('')
        self.total_frags += 1
        if not frag.weapon in self.weapons:
            self.add_weapon(frag.weapon)
        if not frag.fraggee in self.adversaries:
            self.add_adversary(frag.fraggee)
        self.weapon_frags[frag.weapon] += 1
        self.player_frags[frag.fraggee] += 1
        self.player_weapon_frags[frag.fraggee][frag.weapon] += 1
        if self.stat_container:
            self.stat_container.add_frag(frag)

    def add_death(self, death):
        logging.getLogger('').debug('')
        self.total_deaths += 1
        if not death.weapon in self.weapons:
            self.add_weapon(death.weapon)
        if not death.fragger in self.adversaries:
            self.add_adversary(death.fragger)
        self.weapon_deaths[death.weapon] += 1
        self.player_deaths[death.fragger] += 1
        self.player_weapon_deaths[death.fragger][death.weapon] += 1
        if self.stat_container:
            self.stat_container.add_death(death)

    def exportables(self):
        logging.getLogger('').debug('')
        out = []
        for x in BaseStatKeeper.exportables(self):
            if x[0] != 'map' and \
              (('map' in self and x[1] != self.map) or \
               ('map' not in self)) and \
               x[0] != 'zserv' and \
              (('zserv' in self and x[1] != self.zserv) or \
               ('zserv' not in self)):
                out.append(x)
        possible_aliases = \
                get_possible_aliases(self.name, self.encoded_name, [self.ip])
        if possible_aliases:
            out.append(('possible_player_aliases', Listable(possible_aliases)))
        else:
            out.append(('possible_player_aliases', None))
        return out

    def set_map(self, map):
        logging.getLogger('').debug('')
        self.map = map
        self.stat_container = self.map

    def __str__(self):
        return "<Player [%s]>" % (self.name)

    def __repr__(self):
        return "Player(%s)" % (self.name)

    def get_frag_dict(self):
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

    def export(self):
        d = BaseStatKeeper.export(self)
        d.update(self.get_frag_dict())
        return d

    def export_summary(self):
        ###
        # Values:
        #   Player, Overall Frag/Death Ratio,
        #   Per-Weapon Frags/Deaths/Ratio, Per-Player Frags/Deaths/Ratio
        #   Flag Take/Cap Ratio, Flag Drop/Return Ratio, 
        ###
        d = self.export()
        weapons = sorted(d['weapons'].keys())
        adversaries = sorted(d['adversaries'].keys())
        columns = ['Player', 'Frag/Death %']
        values = [self.name, get_ratio(self.total_frags, self.total_deaths)]
        for weapon in weapons:
            columns.append('Frag with %s' % (weapon))
            values.append(d['weapons'][weapon]['frags'])
            columns.append('Death by %s' % (weapon))
            values.append(d['weapons'][weapon]['deaths'])
            columns.append('Ratio with %s' % (weapon))
            values.append(d['weapons'][weapon]['ratio'])
        for adversary in adversaries:
            columns.append('Fragged %s' % (adversary))
            values.append(d['adversaries'][adversary]['frags'])
            columns.append('Fragged by %s' % (adversary))
            values.append(d['adversaries'][adversary]['deaths'])
            columns.append('Ratio against %s' % (adversary))
            values.append(d['adversaries'][adversary]['ratio'])
        return dict(zip(columns, values))

