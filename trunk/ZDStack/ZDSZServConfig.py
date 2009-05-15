from __future__ import with_statement

import os
import logging

from decimal import Decimal
from ConfigParser import NoOptionError

from ZDStack import TEAM_COLORS, get_zdslog
from ZDStack.Utils import check_ip, resolve_path, requires_instance_lock
from ZDStack.ZDSConfigParser import ZDSConfigParser

zdslog = get_zdslog()

class ZServConfigParser(ZDSConfigParser):

    """ZServConfigParser parses a config for a ZServ.

    ZServConfigParser contains special methods for obtaining ZServ
    configuration values.

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
        """ZServConfigParsers don't support adding sections."""
        raise NotImplementedError()

    def has_section(self, *args, **kwargs):
        """ZServConfigParsers don't support sections."""
        raise NotImplementedError()

    def remove_section(self, *args, **kwargs):
        raise NotImplementedError()

    @requires_instance_lock()
    def clear(self):
        """Removes all data for this ZServ's config."""
        ZDSConfigParser.remove_section(self, self.zserv.name,
                                       acquire_lock=False)

    @requires_instance_lock()
    def has_option(self, option):
        """Checks if this ZServ's config contains a specific option.

        :param option: the option to check for
        :type option: string
        :rtype: boolean

        """
        return ZDSConfigParser.has_option(self, self.zserv.name, option,
                                          acquire_lock=False)

    @requires_instance_lock()
    def options(self):
        """Gets this ZServ's config's options.

        :rtype: list of strings
        :returns: a list of strings representing the names of the
                  options

        """
        return ZDSConfigParser.options(self, self.zserv.name,
                                       acquire_lock=False)

    @requires_instance_lock()
    def remove_option(self, option):
        """Removes an option from this ZServ's config.

        :param option: the option to be removed
        :type option: string
        :rtype: boolean
        :returns: True if the option existed

        """
        return ZDSConfigParser.remove_option(self, self.zserv.name,
                                             acquire_lock=False)

    @requires_instance_lock()
    def get_raw(self, section, option, default=None):
        """Gets an option's value without interpolation.

        :param section: the name of the section in which to look for
                        the option
        :type section: string
        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: string
        :returns: the string value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        The 'section' parameter is ignored, replaced by
        self.zserv.name.  The signature is as it is because it's called
        by other methods that aren't overridden here.

        """
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

    @requires_instance_lock()
    def get(self, option, default=None):
        """Gets an option's value.

        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: string
        :returns: the string value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
        return ZDSConfigParser.get(self, self.zserv.name, option, default,
                                   acquire_lock=False)

    @requires_instance_lock()
    def _get(self, conv, option, default=None):
        val = self.get(option, default, acquire_lock=False)
        if val:
            return conv(val)
        else:
            return val

    @requires_instance_lock()
    def getint(self, option, default=None):
        """Gets an option's value as an int.

        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: int
        :returns: the int value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
        return self._get(int, option, default, acquire_lock=False)

    @requires_instance_lock()
    def getfloat(self, option, default=None):
        """Gets an option's value as a float.

        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: float
        :returns: the float value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
        return self._get(float, option, default, acquire_lock=False)

    def _getpercent(self, x):
        d = Decimal(x)
        if d < 1:
            d = d * Decimal(100)
        return d

    @requires_instance_lock()
    def getpercent(self, option, default=None):
        """Gets an option's value as a percentage.

        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: string
        :returns: the string value of the option (as a percentage) if
                  found.  If the option is not found, but 'default' is
                  not None, the value of the 'default' argument will be
                  returned.  Otherwise a NoOptionError is raised.

        The returned percentage will never be higher than 100%, use
        'getdecimal()' for that.

        """
        return self._get(self._getpercent, option, default, acquire_lock=False)

    @requires_instance_lock()
    def getdecimal(self, option, default=None):
        """Gets an option's value as a Decimal.

        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: Decimal
        :returns: the Decimal value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
        return self._get(Decimal, option, default, acquire_lock=False)

    @requires_instance_lock()
    def getlist(self, option, default=None, parse_func=None):
        """Gets an option's value as a list.

        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :param parse_func: a function used to parse the option's value
                           into a list.  optional, the default is:
                           'lambda x: [y.strip() for y in x.split(',')]'
        :type parse_func: function
        :rtype: list
        :returns: the parsed list value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
        if not parse_func:
            parse_func = lambda x: [y.strip() for y in x.split(',')]
        return self._get(parse_func, option, default, acquire_lock=False)

    @requires_instance_lock()
    def getboolean(self, option, default=None):
        """Gets an option's value as a boolean.

        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: boolean
        :returns: the boolean value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
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

    @requires_instance_lock()
    def getpath(self, option, default=None):
        """Gets an option's value as a resolved path.

        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: string
        :returns: the string value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.  The value will
                  be passed through
                  os.path.abspath(os.path.expanduser(v)).

        """
        return self._get(resolve_path, option, default, acquire_lock=False)

    @requires_instance_lock()
    def items(self):
        """Gets this ZServ's config's items.

        :rtype: list of 2-Tuples
        :returns: a list of a section's options and values, i.e.
                  [('option', 'value1'), ('option2', 'value2')]

        """
        return self._sections[self.zserv.name].items()

    def process_config(self, reload=False):
        """Process a config.

        :param reload: whether or not to reload the configuration
        :type reload: boolean

        After the config has been successfully processed, this
        ZServConfig updates its ZServ's instance variables

        """
        from ZDStack.ZServ import DUEL_MODES
        if reload:
            self.reload()
        game_mode = self.zserv.zdstack.config.get(self.zserv.name, 'mode')
        self.game_mode = game_mode.lower()
        zserv_folder = self.getpath('zdstack_zserv_folder')
        zserv_exe = self.getpath('zserv_exe')
        home_folder = os.path.join(zserv_folder, self.zserv.name)
        config_file = os.path.join(home_folder, self.zserv.name + '.cfg')
        banlist_file = os.path.join(home_folder, 'zd_bans.txt')
        if not os.path.isdir(home_folder):
            os.mkdir(home_folder)
        fifo_path = os.path.join(home_folder, 'zdsfifo')
        if os.path.exists(fifo_path) and os.path.isdir(fifo_path):
            es = "[%s]: FIFO [%s] cannot be created, a folder with the same "
            es += "name already exists"
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
        ip = self.get('ip')
        if ip:
            check_ip(ip)
        ###
        # Normally, we would disable stats when using fakezserv, but let's
        # assume whoever is using fakezserv knows what they're doing.
        ###
        if 'fakezserv' in zserv_exe:
            cmd = [zserv_exe, self.getpath('fake_logfile'), fifo_path]
            # stats_enabled = False
        else:
            cmd = [zserv_exe, '-cfg', config_file, '-waddir', wad_folder,
                   '-iwad', iwad, '-port', str(port), '-log']
            for wad in wads:
                cmd.extend(['-file', wad])
            if ip:
                cmd.extend(['-ip', ip])
            # stats_enabled = self.getboolean('enable_stats', False)
        events_enabled = self.getboolean('enable_events', False)
        stats_enabled = self.getboolean('enable_stats', False)
        plugins_enabled = self.getboolean('enable_plugins', False)
        if not events_enabled:
            if stats_enabled:
                es = "Statistics require events, but they have been disabled"
                raise ValueError(es)
            if plugins_enabled:
                es = "Plugins require events, but they have been disabled"
                raise ValueError(es)
        save_logfile = self.getboolean('save_logfile', False)
        if not save_logfile:
            ###
            # This can be confusing, I admit.
            ###
            save_logfile = self.getboolean('save_logfiles', False)
        use_global_banlist = self.getboolean('use_global_banlist', False)
        use_global_whitelist = self.getboolean('use_global_whitelist', False)
        copy_zdaemon_banlist = self.getboolean('copy_zdaemon_banlist', False)
        whitelist_file = self.getpath('whitelist_file', None)
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
        maps = self.getlist('maps') or ['map01']
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
            zdslog.debug("Setting up %s's logger" % (self.zserv.name))
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
        self.zserv.config_file = config_file
        if hasattr(self.zserv, 'banlist_file') and not \
           self.zserv.banlist_file == banlist_file:
            ###
            # The banlist should be reloaded.
            ###
            self.zserv.banlist_file = banlist_file
            self.zserv.banlist = BanList(filename=banlist_file)
        else:
            self.zserv.banlist_file = banlist_file
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
        self.zserv.game_mode = self.game_mode
        self.zserv.events_enabled = events_enabled
        self.zserv.stats_enabled = stats_enabled
        self.zserv.plugins_enabled = plugins_enabled
        self.zserv.save_logfile = save_logfile
        ds = "save_logfile is %s for %s"
        zdslog.debug(ds % (self.zserv.save_logfile, self.zserv.name))
        self.zserv.use_global_banlist = use_global_banlist
        self.zserv.use_global_whitelist = use_global_whitelist
        self.zserv.copy_zdaemon_banlist = copy_zdaemon_banlist
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
        # All server variables
        #
        # sv_fineticks
        # sv_vampire
        # sv_voodoo_spawns
        # sv_useblocking
        # sv_keys_stay
        # sv_keys_teamkeys
        # sv_keys_inteammodes
        # sv_no_team_starts
        # sv_ctf_old_convention
        # sv_allow_target_names
        # sv_hide_countries
        # sv_powerful_monsters
        # sv_strong_monsters
        # sv_silentbfg
        # sv_oldjump
        # sv_oldweaponswitch "false"
        # sv_oldrandom "false"
        # sv_oldpmovement "false"
        # sv_oldsoundcut "false"
        # sv_oldwallrun "false"
        # sv_oldwepsound "true"
        # sv_keepkeys "false"
        # sv_niceweapons "false"
        # sv_samespawnspot "false"
        # sv_barrelrespawn "false"
        # sv_respawnprotect "false"
        # sv_weapondrop "false"
        # * sv_telemissiles "false"
        # sv_quadrespawntime "false"
        # sv_resetinventory "false"
        # sv_nocrosshair "false"
        # sv_nosuper "false"
        # sv_noexitkill "false"
        # sv_nopassover "false"
        # sv_respawnsuper "true"
        # sv_nofreelook "false"
        # sv_nojump "false"
        # sv_fastmonsters "false"
        # sv_itemrespawn "true"
        # sv_monsterrespawn "false"
        # sv_nomonsters "true"
        # sv_infiniteammo "false"
        # sv_noexit "true"
        # sv_noarmor "false"
        # * sv_forcerespawn "false"
        # sv_spawnfarthest "false"
        # sv_samelevel "false"
        # sv_oldfalldamage "false"
        # sv_falldamage "false"
        # sv_weaponstay "true"
        # sv_noitems "false"
        # sv_nohealth "false"
        # sv_randmaps
        # acl
        # - this also needs commands acl_add/acl_remove/acl_clear
        # * maxplayersperteam "0"
        # * spam_limit "10"
        # * spam_window "10"
        # * maxteams "2"
        # * teamscorelimit "5"
        # * killlimit "0"
        # * timelimit "15"
        # * fraglimit "0"
        # * teamdamage "0"
        # var_pushers "true"
        # var_friction "true"
        # developer "false"
        # nofilecompression "false"
        # * teamplay "1"
        # * ctf "1"
        # * deathmatch "1"
        # * skill "4"
        # * sv_deathlimit "180"
        # sv_showmultikills "true"
        # sv_showsprees "true"
        # sv_splashfactor "1"
        # sv_teamautoaim "0"
        # addrocketexplosion "false"
        # cl_missiledecals "true"
        # * sv_gravity "800"
        # genblockmap "false"
        # forcewater "false"
        # * sv_aircontrol "0"
        # * maxclients "16"
        # sv_unlag "true"
        # sv_unlag_report "false"
        # * sv_vote_min "50"
        # * sv_vote_randcaps "0"
        # * sv_vote_randmap "0"
        # * sv_vote_kick_percent "60"
        # * sv_vote_kick "0"
        # * sv_vote_reset "0"
        # * sv_vote_map "0"
        # * sv_vote_map_percent "51"
        # * sv_vote_map_skip "0"
        # * sv_vote_timeout "45"
        # * sv_vote_limit "3"
        # * specs_dont_disturb_players "0"
        # * sv_maxclientsperip "4"
        # * password "zdstackpassword"
        # * master_advertise "0"
        # * restartemptymap "0"
        # * removebotswhenhumans "1"
        # * minplayers "0"
        # * maxplayers "8"
        # * cfg_activated "1"
        # * rcon_cmds_9 ""
        # * rcon_cmds_8 ""
        # * rcon_cmds_7 ""
        # * rcon_cmds_6 ""
        # * rcon_cmds_5 ""
        # * rcon_cmds_4 ""
        # * rcon_cmds_3 ""
        # * rcon_cmds_2 ""
        # * rcon_cmds_1 "mapskipto players"
        # * rcon_pwd_9 ""
        # * rcon_pwd_8 ""
        # * rcon_pwd_7 ""
        # * rcon_pwd_6 ""
        # * rcon_pwd_5 ""
        # * rcon_pwd_4 ""
        # * rcon_pwd_3 ""
        # * rcon_pwd_2 ""
        # * rcon_pwd_1 "zdstacklevel1"
        # * rcon_password "zdstackrcon"
        # * motd "ZDStack Server ctf<br><br>This server is managed by ZDStack"
        # banlist_url ""
        # * hostname "ZDStack Server Private CTF ctf"
        # * optional_wads "zvox2.wad"
        # * email "zdstack@zdstack.com"
        # website "http://zdstack.com/wads"
        # sv_resend "1"
        # wi_percents "true"
        # heapsize "8"
        # cl_maxdecals "1024"
        # cl_spreaddecals "true"
        # limitpainelemental "true"
        # r_stretchsky "true"
        # * log_disposition "2"
        #
        ###

        ###
        # Stuff added in 1.09 (and maybe 1.08.08 RCs
        #
        # sv_specteamblock
        # sv_oldthrust
        # sv_allowzoom
        # item_respawn_time
        # cl_interp (0 is equivalent to sv_finetics 1.08) 0 - 5
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
        """Gets configuration data.

        :rtype: string
        :returns: configuration data as a string in zserv configuration format

        """
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
        if self.zserv.use_global_banlist:
            addr = (self.zserv.zdstack.hostname, self.zserv.zdstack.port)
            banlist_url = 'http://%s:%s/bans' % addr
            add_var_line(banlist_url, 'set banlist_url "%s"')
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
        add_bool_line(self.zserv.game_mode in DM_MODES,
                      'set deathmatch "%s"')
        if add_bool_line(self.zserv.game_mode in TEAM_MODES, \
                                                        'set teamplay "%s"'):
            add_var_line(self.zserv.scorelimit, 'set teamscorelimit "%s"')
        add_bool_line(self.zserv.game_mode in CTF_MODES, 'set ctf "%s"')
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
        if self.zserv.game_mode in DUEL_MODES:
            self.zserv.max_players = 2
        add_var_line(self.zserv.max_players, 'set maxplayers "%s"')
        add_var_line(self.zserv.timelimit, 'set timelimit "%s"')
        add_var_line(self.zserv.fraglimit, 'set fraglimit "%s"')
        add_var_line(self.zserv.auto_respawn, 'set sv_autorespawn "%s"')
        add_var_line(self.zserv.teamdamage, 'set teamdamage "%s"')
        add_var_line(self.zserv.max_teams, 'set maxteams "%s"')
        return self._new_template

