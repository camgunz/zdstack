from __future__ import with_statement

import os
import logging

from decimal import Decimal
from ConfigParser import NoOptionError

from ZDStack import TEAM_COLORS, get_zdslog
from ZDStack.Utils import check_ip, resolve_path, requires_lock
from ZDStack.ZDSConfigParser import ZDSConfigParser

zdslog = get_zdslog()

class ZServConfigParser(ZDSConfigParser):

    """ZServConfigParser parses a config for a ZServ.

    ZSCP contains special methods for obtain ZServ configuration
    values.

    """

    def __init__(self, zserv):
        ZDSConfigParser.__init__(self, zserv.zdstack.config.filename)
        if not zserv.name in self.sections():
            es = "Configuration file contains no configuration data for %s"
            raise ValueError(es % (zserv.name))
        self.zserv = zserv
        self.game_mode = zserv.zdstack.config.get(zserv.name, 'mode').lower()
        self.set(self.zserv.name, 'name', self.zserv.name)

    def add_section(self, *args, **kwargs):
        raise NotImplementedError()

    def has_section(self, *args, **kwargs):
        raise NotImplementedError()

    def remove_section(self, *args, **kwargs):
        raise NotImplementedError()

    @requires_lock(self.lock)
    def has_option(self, option):
        return ZDSConfigParser.has_option(self, self.zserv.name, option,
                                          acquire_lock=False)

    @requires_lock(self.lock)
    def options(self):
        return ZDSConfigParser.options(self, self.zserv.name,
                                       acquire_lock=False)

    @requires_lock(self.lock)
    def remove_option(self, option):
        return ZDSConfigParser.remove_option(self, self.zserv.name,
                                             acquire_lock=False)

    @requires_lock(self.lock)
    def get_raw(self, section, option, default=None):
        opt = self.optionxform(option)
        game_mode_opt = '_'.join([self.game_mode, opt])
        section = self.zserv.name
        if opt in self._sections[section]:
            return self._sections[section][opt]
        elif game_mode_opt in self._sections[section]:
            return self._sections[section][game_mode_opt]
        elif game_mode_opt in self._defaults:
            return self._defaults[game_mode_opt]
        elif opt in self._defaults:
            return self._defaults[opt]
        else:
            return default

    @requires_lock(self.lock)
    def get(self, option, default=None):
        return ZDSConfigParser.get(self, self.zserv.name, option, default,
                                   acquire_lock=False)

    @requires_lock(self.lock)
    def _get(self, conv, option, default=None):
        val = self.get(option, default, acquire_lock=False)
        if val:
            return conv(val)
        else:
            return val

    @requires_lock(self.lock)
    def getint(self, option, default=None):
        return self._get(int, option, default, acquire_lock=False)

    @requires_lock(self.lock)
    def getfloat(self, option, default=None):
        return self._get(float, option, default, acquire_lock=False)

    def _getpercent(self, x):
        d = Decimal(x)
        if d < 1:
            d = d * Decimal(100)
        return d

    @requires_lock(self.lock)
    def getpercent(self, option, default=None):
        return self._get(self._getpercent, option, default, acquire_lock=False)

    @requires_lock(self.lock)
    def getdecimal(self, option, default=None):
        return self._get(Decimal, option, default, acquire_lock=False)

    @requires_lock(self.lock)
    def getlist(self, option, default=None, parse_func=None):
        if not parse_func:
            parse_func = lambda x: [y.strip() for y in x.split(',')]
        return self._get(parse_func, option, default, acquire_lock=False)

    @requires_lock(self.lock)
    def getboolean(self, option, default=None):
        try:
            v = self.get(option, default, acquire_lock=False)
            if v == default or not v:
                return default
            if isinstance(v, basestring):
                lv = v.lower()
            if lv not in self._boolean_states:
                raise ValueError("Not a boolean: %s" % (v))
            return self._boolean_states[lv]
        except NoOptionError:
            return default

    @requires_lock(self.lock)
    def getpath(self, option, default=None):
        return self._get(resolve_path, option, default, acquire_lock=False)

    @requires_lock(self.lock)
    def items(self):
        return self._sections[self.zserv.name].items()

    def process_config(self):
        """Process a config

        config: a RawZDSConfigParser instance or subclass.

        """
        from ZDStack.ZServ import DUEL_MODES
        game_mode = self.zserv.zdstack.config.get(zserv.name, 'mode').lower()
        self.game_mode = game_mode
        zserv_folder = self.getpath('zdstack_zserv_folder')
        zserv_exe = self.getpath('zserv_exe')
        home_folder = os.path.join(zserv_folder, self.zserv.name)
        configfile = os.path.join(home_folder, self.zserv.name + '.cfg')
        if not os.path.isdir(home_folder):
            os.mkdir(home_folder)
        fifo_path = os.path.join(home_folder, 'zdsfifo')
        if os.path.exists(fifo_path):
            if os.path.isdir(fifo_path):
                es = "[%s]: FIFO [%s] cannot be created, a folder with the "
                es += "same name already exists"
                raise Exception(es % (self.zserv.name, fifo_path))
        wad_folder = self.getpath('zdstack_wad_folder')
        iwad_folder = self.getpath('zdstack_iwad_folder')
        base_iwad = os.path.expanduser(self.get('iwad'))
        if os.path.isabs(base_iwad):
            iwad = resolve_path(base_iwad)
        else:
            iwad = os.path.join(iwad_folder, os.path.basename(base_iwad))
        wads = self.getlist('wads', default=[])
        for wad in wads:
            wad_path = os.path.join(wad_folder, wad)
            if not os.path.isfile(wad_path) or os.path.islink(wad_path):
                es = "%s: WAD [%s] not found"
                raise ValueError(es % (self.zserv.name, wad_path))
        port = self.getint('port')
        cmd = [zserv_exe, '-cfg', configfile, '-waddir', wad_folder, '-iwad',
               iwad, '-port', str(port), '-log']
        for wad in wads:
            cmd.extend(['-file', wad])
        ip = self.get('ip')
        if ip:
            check_ip(ip)
            cmd.extend(['-ip', ip])
        events_enabled = self.getboolean('enable_events', False)
        stats_enabled = self.getboolean('enable_stats', False)
        plugins_enabled = self.getboolean('enable_plugins', False)
        save_logfile = self.getboolean('save_logfile', False)
        if not events_enabled:
            if stats_enabled:
                es = "Statistics require events, but they have been disabled"
                raise ValueError(es)
            if plugins_enabled:
                es = "Plugins require events, but they have been disabled"
                raise ValueError(es)
        rcon_password = self.get('rcon_password')
        rcon_enabled = rcon_password and True
        rps = 'rcon_password_'
        rcs = 'rcon_commands_'
        pf = lambda x: x.split()
        lf = lambda x: [y.split('=') for y in x.split()]
        rcon_password_1 = self.get(rps + '1')
        rcon_password_2 = self.get(rps + '2')
        rcon_password_3 = self.get(rps + '3')
        rcon_password_4 = self.get(rps + '4')
        rcon_password_5 = self.get(rps + '5')
        rcon_password_6 = self.get(rps + '6')
        rcon_password_7 = self.get(rps + '7')
        rcon_password_8 = self.get(rps + '8')
        rcon_password_9 = self.get(rps + '9')
        rcon_commands_1 = rcon_password_1 and self.getlist(rcs + '1', None, pf)
        rcon_commands_2 = rcon_password_2 and self.getlist(rcs + '2', None, pf)
        rcon_commands_3 = rcon_password_3 and self.getlist(rcs + '3', None, pf)
        rcon_commands_4 = rcon_password_4 and self.getlist(rcs + '4', None, pf)
        rcon_commands_5 = rcon_password_5 and self.getlist(rcs + '5', None, pf)
        rcon_commands_6 = rcon_password_6 and self.getlist(rcs + '6', None, pf)
        rcon_commands_7 = rcon_password_7 and self.getlist(rcs + '7', None, pf)
        rcon_commands_8 = rcon_password_8 and self.getlist(rcs + '8', None, pf)
        rcon_commands_9 = rcon_password_9 and self.getlist(rcs + '9', None, pf)
        server_password = self.get('server_password')
        requires_password = server_password is not None
        deathlimit = self.getint('deathlimit')
        spam_window = self.getint('spam_window')
        spam_limit = self.getint('spam_window')
        speed_check = self.getboolean('speed_check')
        restart_empty_map = self.getboolean('restart_empty_map')
        vote_limit = self.getint('vote_limit')
        vote_timeout = self.getint('vote_timeout')
        vote_reset = self.getboolean('vote_reset')
        vote_map = self.getboolean('vote_map')
        vote_map_percent = vote_map and self.getpercent('vote_map_percent')
        vote_map_skip = vote_map and self.getint('vote_map_skip')
        vote_kick = self.getboolean('vote_kick')
        vote_kick_percent = self.getpercent('vote_kick_percent')
        admin_email = self.get('admin_email')
        advertise = self.getboolean('advertise')
        hostname = self.get('hostname')
        website = self.get('website')
        motd = self.get('motd')
        add_mapnum_to_hostname = self.getboolean('add_mapnum_to_hostname')
        remove_bots_when_humans = self.getboolean('remove_bots_when_humans')
        maps = self.getlist('maps')
        optional_wads = self.getlist('optional_wads')
        alternate_wads = self.getlist('alternate_wads', parse_func=lf)
        ###
        # TODO: support setting overtime on individual maps
        ###
        overtime = self.getboolean('overtime')
        skill = self.getint('skill')
        gravity = self.getdecimal('gravity')
        air_control = self.getdecimal('air_control')
        telemissiles = self.getboolean('telemissiles')
        specs_dont_disturb_players = \
                                self.getboolean('specs_dont_disturb_players')
        min_players = self.getint('min_players')
        dmflags = self.get('dmflags')
        dmflags2 = self.get('dmflags2')
        max_clients = self.getint('max_clients')
        max_players = \
            self.game_mode in DUEL_MODES and 2 or self.getint('max_players')
        timelimit = self.getint('timelimit')
        fraglimit = self.getint('fraglimit')
        auto_respawn = self.getint('auto_respawn')
        teamdamage = self.getdecimal('teamdamage')
        max_teams = self.getint('max_teams')
        zdslog.debug("Max Teams: %s" % (max_teams))
        playing_colors = max_teams and TEAM_COLORS[:max_teams]
        max_players_per_team = self.getint('max_players_per_team')
        scorelimit = self.getint('team_score_limit')
        ###
        # At this point, everything parsed OK.  So it's now save to update
        # our ZServ's instance attributes.
        ###
        ###
        # We want to setup the ZServ's logger here too, if applicable.
        ###
        if save_logfile:
            cp = self.zserv.zdstack.config
            to_keep = self.getint('number_of_zserv_logs_to_backup')
            to_keep = to_keep or 0
            log_folder = cp.getpath('DEFAULT', 'zdstack_log_folder')
            log_file = os.path.join(log_folder, self.zserv.name + '.log')
            h = logging.handlers.TimedRotatingFileHandler(log_file,
                                                          when='midnight',
                                                          backupCount=to_keep)
            h.setFormatter(logging.Formatter('%(message)s'))
            logger = logging.getLogger(self.zserv.name)
            logger.addHandler(h)
            logger.setLevel(logging.INFO)
        self.zserv.home_folder = home_folder
        self.zserv.configfile = configfile
        self.zserv.zserv_exe = zserv_exe
        self.zserv.fifo_path = fifo_path
        self.zserv.wad_folder = wad_folder
        self.zserv.iwad_folder = iwad_folder
        self.zserv.base_iwad = base_iwad
        self.zserv.iwad = iwad
        self.zserv.wads = wads
        self.zserv.port = port
        self.zserv.cmd = cmd
        self.zserv.ip = ip
        self.zserv.raw_game_mode = self.game_mode
        self.zserv.events_enabled = events_enabled
        self.zserv.stats_enabled = stats_enabled
        self.zserv.plugins_enabled = plugins_enabled
        self.zserv.save_logfile = save_logfile
        self.zserv.rcon_password = rcon_password
        self.zserv.rcon_enabled = rcon_enabled
        self.zserv.rcon_password_1 = rcon_password_1
        self.zserv.rcon_password_2 = rcon_password_2
        self.zserv.rcon_password_3 = rcon_password_3
        self.zserv.rcon_password_4 = rcon_password_4
        self.zserv.rcon_password_5 = rcon_password_5
        self.zserv.rcon_password_6 = rcon_password_6
        self.zserv.rcon_password_7 = rcon_password_7
        self.zserv.rcon_password_8 = rcon_password_8
        self.zserv.rcon_password_9 = rcon_password_9
        self.zserv.rcon_commands_1 = rcon_commands_1
        self.zserv.rcon_commands_2 = rcon_commands_2
        self.zserv.rcon_commands_3 = rcon_commands_3
        self.zserv.rcon_commands_4 = rcon_commands_4
        self.zserv.rcon_commands_5 = rcon_commands_5
        self.zserv.rcon_commands_6 = rcon_commands_6
        self.zserv.rcon_commands_7 = rcon_commands_7
        self.zserv.rcon_commands_8 = rcon_commands_8
        self.zserv.rcon_commands_9 = rcon_commands_9
        self.zserv.server_password = server_password
        self.zserv.requires_password = requires_password
        self.zserv.deathlimit = deathlimit
        self.zserv.spam_window = spam_window
        self.zserv.spam_limit = spam_limit
        self.zserv.speed_check = speed_check
        self.zserv.restart_empty_map = restart_empty_map
        self.zserv.vote_limit = vote_limit
        self.zserv.vote_timeout = vote_timeout
        self.zserv.vote_reset = vote_reset
        self.zserv.vote_map = vote_map
        self.zserv.vote_map_percent = vote_map_percent
        self.zserv.vote_map_skip = vote_map_skip
        self.zserv.vote_kick = vote_kick
        self.zserv.vote_kick_percent = vote_kick_percent
        self.zserv.admin_email = admin_email
        self.zserv.advertise = advertise
        self.zserv.hostname = hostname
        self.zserv.website = website
        self.zserv.motd = motd
        self.zserv.add_mapnum_to_hostname = add_mapnum_to_hostname
        self.zserv.remove_bots_when_humans = remove_bots_when_humans
        self.zserv.maps = maps
        self.zserv.optional_wads = optional_wads
        self.zserv.alternate_wads = alternate_wads
        self.zserv.overtime = overtime
        self.zserv.skill = skill
        self.zserv.gravity = gravity
        self.zserv.air_control = air_control
        self.zserv.telemissiles = telemissiles
        self.zserv.specs_dont_disturb_players = specs_dont_disturb_players
        self.zserv.min_players = min_players
        self.zserv.dmflags = dmflags
        self.zserv.dmflags2 = dmflags2
        self.zserv.max_clients = max_clients
        self.zserv.max_players = max_players
        self.zserv.timelimit = timelimit
        self.zserv.fraglimit = fraglimit
        self.zserv.scorelimit = scorelimit
        self.zserv.auto_respawn = auto_respawn
        self.zserv.teamdamage = teamdamage
        self.zserv.max_teams = max_teams
        self.zserv.playing_colors = playing_colors
        self.zserv.max_players_per_team = max_players_per_team
        self.zserv.team_score_limit = scorelimit
        ###
        # Stuff still missing
        #
        # sv_fineticks
        #
        ###
        ###
        # Stuff added in 1.09 (and maybe 1.08.08 RCs
        ###
        # sv_specteamblock
        # sv_oldthrust
        # sv_allowzoom
        # item_respawn_time
        # cl_interp (0 is equivalent to 1.08) 0 - 5
        #
        # sv_fineticks is replaced (sorta) by cl_updatemod:
        #
        # 1: updates all positions on every tick: best accuracy, but also
        #    highest bandwith -- equivalent to sv_fineticks "1"
        # 2: updates all positions every 2 ticks: medium accuracy, lower
        #    bandwidth
        # 3: updates all postions every 3 ticks: lower accuracy, lowest
        #    bandwidth 
        ###

    def get_config_data(self):
        from ZDStack.ZServ import DUEL_MODES, DM_MODES, TEAM_MODES, CTF_MODES
        self._new_template = ''
        def add_line(should_add, line):
            if should_add:
                self._new_template += line + '\n'
                return True
            return False
        def add_bool_line(bool, line):
            if bool:
                line = line % ('1')
            else:
                line = line % ('0')
            if add_line(True, line):
                return bool
            return False
        def add_var_line(var, line):
            return add_line(var, line % (var))
        add_line(True, 'set cfg_activated "1"')
        ###
        # 0: old logs are left in self.zserv.home_folder.
        # 1: old logs are moved to self.zserv.home_folder/old-logs.
        # 2: old logs are deleted.
        ###
        add_line(True, 'set log_disposition "2"')
        add_var_line(self.zserv.hostname, 'set hostname "%s"')
        add_var_line(self.zserv.motd, 'set motd "%s"')
        add_var_line(self.zserv.website, 'set website "%s"')
        add_var_line(self.zserv.admin_email, 'set email "%s"')
        add_bool_line(self.zserv.advertise, 'set master_advertise "%s"')
        if add_bool_line(self.zserv.rcon_enabled, 'set enable_rcon "%s"'):
            add_var_line(self.zserv.rcon_password, 'set rcon_password "%s"')
        if add_bool_line(self.zserv.requires_password, \
                                                    'set force_password "%s"'):
            add_var_line(self.zserv.server_password, 'set password "%s"')
        add_var_line(self.zserv.deathlimit, 'set sv_deathlimit "%s"')
        add_var_line(self.zserv.spam_window, 'set spam_window "%s"')
        add_var_line(self.zserv.spam_limit, 'set spam_limit "%s"')
        add_bool_line(self.zserv.speed_check, 'set speed_check "%s"')
        add_var_line(self.zserv.vote_limit, 'set sv_vote_limit "%s"')
        add_var_line(self.zserv.vote_timeout, 'set sv_vote_timeout "%s"')
        add_bool_line(self.zserv.vote_reset, 'set sv_vote_reset "%s"')
        add_bool_line(self.zserv.vote_map, 'set sv_vote_map "%s"')
        add_var_line(self.zserv.vote_map_percent, 'set sv_vote_map_percent "%s"')
        add_var_line(self.zserv.vote_map_skip, 'set sv_vote_map_skip "%s"')
        add_var_line(self.zserv.vote_kick, 'set sv_vote_kick "%s"')
        add_var_line(self.zserv.vote_kick_percent,
                     'set sv_vote_kick_percent "%s"')
        if self.zserv.rcon_password_1 and self.zserv.rcon_commands_1:
            add_var_line(self.zserv.rcon_password_1, 'set rcon_pwd_1 "%s"')
            add_var_line(' '.join(self.zserv.rcon_commands_1),
                         'set rcon_cmds_1 "%s"')
        if self.zserv.rcon_password_2 and self.zserv.rcon_commands_2:
            add_var_line(self.zserv.rcon_password_2, 'set rcon_pwd_2 "%s"')
            add_var_line(' '.join(self.zserv.rcon_commands_2),
                         'set rcon_cmds_2 "%s"')
        if self.zserv.rcon_password_3 and self.zserv.rcon_commands_3:
            add_var_line(self.zserv.rcon_password_3, 'set rcon_pwd_3 "%s"')
            add_var_line(' '.join(self.zserv.rcon_commands_3),
                         'set rcon_cmds_3 "%s"')
        if self.zserv.rcon_password_4 and self.zserv.rcon_commands_4:
            add_var_line(self.zserv.rcon_password_4, 'set rcon_pwd_4 "%s"')
            add_var_line(' '.join(self.zserv.rcon_commands_4),
                         'set rcon_cmds_4 "%s"')
        if self.zserv.rcon_password_5 and self.zserv.rcon_commands_5:
            add_var_line(self.zserv.rcon_password_5, 'set rcon_pwd_5 "%s"')
            add_var_line(' '.join(self.zserv.rcon_commands_5),
                         'set rcon_cmds_5 "%s"')
        if self.zserv.rcon_password_6 and self.zserv.rcon_commands_6:
            add_var_line(self.zserv.rcon_password_6, 'set rcon_pwd_6 "%s"')
            add_var_line(' '.join(self.zserv.rcon_commands_6),
                         'set rcon_cmds_6 "%s"')
        if self.zserv.rcon_password_7 and self.zserv.rcon_commands_7:
            add_var_line(self.zserv.rcon_password_7, 'set rcon_pwd_7 "%s"')
            add_var_line(' '.join(self.zserv.rcon_commands_7),
                         'set rcon_cmds_7 "%s"')
        if self.zserv.rcon_password_8 and self.zserv.rcon_commands_8:
            add_var_line(self.zserv.rcon_password_8, 'set rcon_pwd_8 "%s"')
            add_var_line(' '.join(self.zserv.rcon_commands_8),
                         'set rcon_cmds_8 "%s"')
        if self.zserv.rcon_password_9 and self.zserv.rcon_commands_9:
            add_var_line(self.zserv.rcon_password_9, 'set rcon_pwd_9 "%s"')
            add_var_line(' '.join(self.zserv.rcon_commands_9),
                         'set rcon_cmds_9 "%s"')
        add_bool_line(self.zserv.raw_game_mode in DM_MODES,
                      'set deathmatch "%s"')
        if add_bool_line(self.zserv.raw_game_mode in TEAM_MODES, \
                                                        'set teamplay "%s"'):
            add_var_line(self.zserv.scorelimit, 'set teamscorelimit "%s"')
        add_bool_line(self.zserv.raw_game_mode in CTF_MODES, 'set ctf "%s"')
        add_bool_line(self.zserv.telemissiles, 'set sv_telemissiles "%s"')
        add_bool_line(self.zserv.specs_dont_disturb_players,
                      'set specs_dont_disturb_players "%s"')
        add_bool_line(self.zserv.restart_empty_map, 'set restartemptymap "%s"')
        if self.zserv.maps:
            for map in self.zserv.maps:
                add_var_line(map, 'addmap "%s"')
        if self.zserv.optional_wads:
            add_var_line(' '.join(self.zserv.optional_wads),
                         'set optional_wads "%s"')
        if self.zserv.alternate_wads:
            y = ' '.join(['='.join(x) for x in self.zserv.alternate_wads])
            add_var_line(y, 'setaltwads "%s"')
        cvar_t = 'add_cvaroverride %%s %s'
        if self.zserv.overtime:
            over_t = cvar_t % ('overtime 1')
        else:
            over_t = cvar_t % ('overtime 0')
        if self.zserv.add_mapnum_to_hostname:
            s = 'hostname "%s - %%s"' % (self.zserv.hostname)
            host_t = cvar_t % (s)
        for map in self.zserv.maps:
            add_var_line(map, over_t)
            if self.zserv.add_mapnum_to_hostname:
                add_line(True, host_t % (map, map.upper()))
        add_var_line(self.zserv.skill, 'set skill "%s"')
        add_var_line(self.zserv.gravity, 'set gravity "%s"')
        add_var_line(self.zserv.air_control, 'set sv_aircontrol "%s"')
        add_var_line(self.zserv.min_players, 'set minplayers "%s"')
        add_bool_line(self.zserv.remove_bots_when_humans,
                      'set removebotswhenhumans "%s"')
        add_var_line(self.zserv.dmflags, 'set dmflags "%s"')
        add_var_line(self.zserv.dmflags2, 'set dmflags2 "%s"')
        add_var_line(self.zserv.max_clients, 'set maxclients "%s"')
        if self.zserv.raw_game_mode in DUEL_MODES:
            self.zserv.max_players = 2
        add_var_line(self.zserv.max_players, 'set maxplayers "%s"')
        add_var_line(self.zserv.timelimit, 'set timelimit "%s"')
        add_var_line(self.zserv.fraglimit, 'set fraglimit "%s"')
        add_var_line(self.zserv.auto_respawn, 'set sv_autorespawn "%s"')
        add_var_line(self.zserv.teamdamage, 'set teamdamage "%s"')
        add_var_line(self.zserv.max_teams, 'set maxteams "%s"')
        return self._new_template
