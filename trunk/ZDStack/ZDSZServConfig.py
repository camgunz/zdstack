from __future__ import with_statement

import os
import types
import logging
from logging.handlers import TimedRotatingFileHandler

from decimal import Decimal
from ConfigParser import NoOptionError

from ZDStack import TEAM_COLORS, get_zdslog
from ZDStack.Utils import check_ip, resolve_path, requires_instance_lock
from ZDStack.ZDSModels import TeamColor
from ZDStack.ZDSDatabase import global_session
from ZDStack.ZDSConfigParser import ZDSConfigParser

zdslog = get_zdslog()

class ZServTRFH(TimedRotatingFileHandler):

    def emit(self, record):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline
        [N.B. this may be removed depending on feedback]. If exception
        information is present, it is formatted using
        traceback.print_exception and appended to the stream.
        """
        try:
            msg = self.format(record)
            if hasattr(types, "UnicodeType"):
                try:
                    self.stream.write(msg)
                except UnicodeError:
                    self.stream.write(msg.encode("UTF-8"))
            else:
                self.stream.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

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
        ###
        # ZDStack stuff
        ###
        game_mode = self.zserv.zdstack.config.get(self.zserv.name, 'mode')
        self.game_mode = game_mode.lower()
        zserv_folder = self.getpath('zdstack_zserv_folder')
        zserv_exe = self.getpath('zserv_exe')
        home_folder = os.path.join(zserv_folder, self.zserv.name)
        config_file = os.path.join(home_folder, self.zserv.name + '.cfg')
        banlist_file = self.getpath('zdstack_banlist_file', None)
        whitelist_file = self.getpath('zdstack_whitelist_file', None)
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
        save_empty_rounds = self.getboolean('save_empty_rounds', False)
        if not events_enabled:
            if save_empty_rounds:
                es = "Saving of empty rounds requires events, but they have "
                es += "been disabled"
                raise ValueError(es)
            if stats_enabled:
                es = "Statistics require events, but they have been disabled"
                raise ValueError(es)
            if plugins_enabled:
                es = "Plugins require events, but they have been disabled"
                raise ValueError(es)
        if not stats_enabled and save_empty_rounds:
            es = "Saving of empty rounds requires statistics, but they have "
            es += "been disabled"
            raise ValueError(es)
        save_logfile = self.getboolean('save_logfile', False)
        if not save_logfile:
            ###
            # This can be confusing, I admit.
            ###
            save_logfile = self.getboolean('save_log_files', False)
        use_global_banlist = self.getboolean('use_global_banlist', False)
        use_global_whitelist = self.getboolean('use_global_whitelist', False)
        copy_zdaemon_banlist = self.getboolean('copy_zdaemon_banlist', False)
        ###
        # End ZDStack stuff
        ###
        ###
        # ZServ stuff
        ###
        add_mapnum_to_hostname = self.getboolean('add_mapnum_to_hostname')
        add_rocket_explosion = self.getboolean('add_rocket_explosion', False)
        admin_email = self.get('admin_email')
        advertise = self.getboolean('advertise', True)
        air_control = self.get('air_control', '0')
        allow_target_names = self.getboolean('allow_target_names', True)
        lf = lambda x: [y.strip() for y in x.split(',')]
        alternate_wads = self.getlist('alternate_wads', parse_func=lf)
        death_limit = self.getint('death_limit')
        developer = self.getboolean('developer')
        dmflags = self.get('dmflags')
        dmflags2 = self.get('dmflags2')
        drop_weapons = self.getboolean('drop_weapons')
        falling_damage = self.getboolean('falling_damage')
        fast_monsters = self.getboolean('fast_monsters')
        fineticks = self.getboolean('fineticks', False)
        force_respawn = self.getboolean('force_respawn')
        force_water = self.getboolean('force_water', False)
        frag_limit = self.getint('frag_limit')
        generate_block_map = self.getboolean('generate_block_map')
        gravity = self.getint('gravity')
        heapsize = self.getint('heapsize')
        hide_countries = self.getboolean('hide_countries')
        hostname = self.get('hostname')
        infinite_ammo = self.getboolean('infinite_ammo')
        instant_weapon_switching = self.getboolean('instant_weapon_switching')
        keep_keys = self.getboolean('keep_keys')
        keys_in_team_modes = self.getboolean('keys_in_team_modes')
        keys_stay = self.getboolean('keys_stay')
        kill_limit = self.getint('kill_limit')
        log_sent_packets = self.getboolean('log_sent_packets')
        maps = self.getlist('maps') or ['map01']
        max_lost_souls = self.getint('max_lost_souls', 20)
        max_clients = self.getint('max_clients')
        max_clients_per_ip = self.getint('max_clients_per_ip')
        max_players = \
            self.game_mode in DUEL_MODES and 2 or self.getint('max_players')
        max_players_per_team = self.getint('max_players_per_team')
        max_teams = self.getint('max_teams')
        min_players = self.getint('min_players')
        motd = self.get('motd')
        nice_weapons = self.getboolean('nice_weapons')
        no_file_compression = self.getboolean('no_file_compression')
        no_team_starts = self.getboolean('no_team_starts')
        no_armor = self.getboolean('no_armor')
        no_crosshair = self.getboolean('no_crosshair')
        no_exit = self.getboolean('no_exit')
        no_exit_kill = self.getboolean('no_exit_kill')
        no_freelook = self.getboolean('no_freelook')
        no_health = self.getboolean('no_health')
        no_items = self.getboolean('no_items')
        no_jump = self.getboolean('no_jump')
        no_monsters = self.getboolean('no_monsters')
        no_passover = self.getboolean('no_passover') # But what about Jews?!?!
        no_super = self.getboolean('no_super')
        old_ctf_convention = self.getboolean('old_ctf_convention')
        old_falling_damage = self.getboolean('old_falling_damage')
        old_jump = self.getboolean('old_jump')
        old_player_movement = self.getboolean('old_player_movement')
        old_random = self.getboolean('old_random')
        old_sound_cutoff = self.getboolean('old_sound_cutoff')
        old_wallrun = self.getboolean('old_wallrun')
        old_weapon_switch = self.getboolean('old_weapon_switch')
        old_weapon_sounds = self.getboolean('old_weapon_sounds')
        optional_wads = self.getlist('optional_wads')
        ###
        # TODO: support setting overtime on individual maps
        ###
        overtime = self.getboolean('overtime')
        playing_colors = max_teams and TEAM_COLORS[:max_teams]
        powerful_monsters = self.getboolean('powerful_monsters')
        quad_respawn_time = self.getboolean('quad_respawn_time')
        random_maps = self.getboolean('random_maps')
        rcon_password = self.get('rcon_password')
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
        remove_bots_when_humans = self.getboolean('remove_bots_when_humans')
        resend_lost_packets = self.getboolean('resend_lost_packets', True)
        reset_inventory = self.getboolean('reset_inventory')
        respawn_barrels = self.getboolean('respawn_barrels')
        respawn_items = self.getboolean('respawn_items')
        respawn_monsters = self.getboolean('respawn_monsters')
        respawn_protection = self.getboolean('respawn_protection')
        respawn_super_items = self.getboolean('respawn_super_items')
        restart_empty_map = self.getboolean('restart_empty_map')
        same_level = self.getboolean('same_level')
        same_spawn_spot = self.getboolean('same_spawn_spot')
        score_limit = self.getint('team_score_limit')
        server_password = self.get('server_password', '')
        show_killing_sprees = self.getboolean('show_killing_sprees')
        show_multi_kills = self.getboolean('show_multi_kills')
        silent_bfg = self.getboolean('silent_bfg')
        skill = self.getint('skill')
        spam_limit = self.getint('spam_limit')
        spam_window = self.getint('spam_window')
        spawn_farthest = self.getboolean('spawn_farthest')
        specs_dont_disturb_players = \
                                self.getboolean('specs_dont_disturb_players')
        speed_check = self.getboolean('speed_check')
        splash_factor = self.getdecimal('splash_factor')
        strong_monsters = self.getboolean('strong_monsters')
        team_autoaim = self.getboolean('team_autoaim')
        team_damage = self.getboolean('team_damage')
        team_keys = self.getboolean('team_keys')
        telemissiles = self.getboolean('telemissiles')
        time_limit = self.getint('time_limit')
        unlagged = self.getboolean('unlagged')
        use_blocking = self.getboolean('use_blocking')
        vampire_mode = self.getboolean('vampire_mode')
        voodoo_spawns = self.getboolean('voodoo_spawns')
        var_friction = self.getboolean('var_friction')
        var_pushers = self.getboolean('var_pushers')
        weapons_stay = self.getboolean('weapons_stay')
        website = self.get('website')
        ###
        # Voting stuff
        ###
        vote_limit = self.getint('vote_limit')
        vote_timeout = self.getint('vote_timeout')
        minimum_vote_percent = self.getint('minimum_vote_percent')
        kick_voting = self.getboolean('vote_kick')
        kick_vote_percent = self.getpercent('kick_vote_percent')
        map_voting = self.getboolean('map_voting')
        random_map_voting = self.getboolean('random_map_voting')
        skip_map_voting = self.getboolean('skip_map_voting')
        map_reset_voting = self.getboolean('map_reset_voting')
        map_vote_percent = self.getpercent('map_vote_percent')
        random_captain_voting = self.getboolean('random_captain_voting')
        ###
        # End voting stuff
        ###
        rcon_enabled = rcon_password and True
        requires_password = len(server_password) > 0
        with global_session() as session:
            q = session.query(TeamColor)
            q = q.filter(TeamColor.color.in_(TEAM_COLORS))
            team_color_instances = dict([(tc.color, tc) for tc in q.all()])
        ###
        # At this point, everything parsed OK.  So it's now safe to update
        # our ZServ's instance attributes.
        ###
        ###
        # We want to setup the ZServ's logger here too, if applicable.
        ###
        if save_logfile:
            zdslog.debug("Setting up logger for %s" % (self.zserv.name))
            cp = self.zserv.zdstack.config
            to_keep = self.getint('number_of_zserv_logs_to_backup')
            to_keep = to_keep or 0
            log_folder = cp.getpath('DEFAULT', 'zdstack_log_folder')
            log_file = os.path.join(log_folder, self.zserv.name + '.log')
            h = ZServTRFH(log_file, when='midnight', backupCount=to_keep)
            h.setFormatter(logging.Formatter('%(message)s'))
            logger = logging.getLogger(self.zserv.name)
            logger.addHandler(h)
            logger.setLevel(logging.INFO)
        self.zserv.home_folder = home_folder
        self.zserv.config_file = config_file
        self.zserv.banlist_file = banlist_file
        if hasattr(self.zserv, 'banlist_file') and not \
           self.zserv.banlist_file == banlist_file:
            ###
            # The banlist should be reloaded.
            ###
            self.zserv.banlist = BanList(filename=banlist_file)
        self.zserv.whitelist_file = whitelist_file
        if hasattr(self.zserv, 'whitelist_file') and not \
           self.zserv.whitelist_file == whitelist_file:
            ###
            # The whitelist should be reloaded.
            ###
            self.zserv.whitelist = WhiteList(filename=whitelist_file)
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
        self.zserv.save_empty_rounds = save_empty_rounds
        self.zserv.save_logfile = save_logfile
        ds = "save_logfile is %s for %s"
        zdslog.debug(ds % (self.zserv.save_logfile, self.zserv.name))
        self.zserv.use_global_banlist = use_global_banlist
        self.zserv.use_global_whitelist = use_global_whitelist
        self.zserv.copy_zdaemon_banlist = copy_zdaemon_banlist
        self.zserv.add_mapnum_to_hostname = add_mapnum_to_hostname
        self.zserv.add_rocket_explosion = add_rocket_explosion
        self.zserv.admin_email = admin_email
        self.zserv.advertise = advertise
        self.zserv.air_control = air_control
        self.zserv.allow_target_names = allow_target_names
        self.zserv.alternate_wads = alternate_wads
        self.zserv.death_limit = death_limit
        self.zserv.developer = developer
        self.zserv.dmflags = dmflags
        self.zserv.dmflags2 = dmflags2
        self.zserv.drop_weapons = drop_weapons
        self.zserv.falling_damage = falling_damage
        self.zserv.fast_monsters = fast_monsters
        self.zserv.fineticks = fineticks
        self.zserv.force_respawn = force_respawn
        self.zserv.force_water = force_water
        self.zserv.frag_limit = frag_limit
        self.zserv.generate_block_map = generate_block_map
        self.zserv.gravity = gravity
        self.zserv.heapsize = heapsize
        self.zserv.hide_countries = hide_countries
        self.zserv.hostname = hostname
        self.zserv.infinite_ammo = infinite_ammo
        self.zserv.instant_weapon_switching = instant_weapon_switching
        self.zserv.keep_keys = keep_keys
        self.zserv.keys_in_team_modes = keys_in_team_modes
        self.zserv.keys_stay = keys_stay
        self.zserv.kill_limit = kill_limit
        self.zserv.log_sent_packets = log_sent_packets
        self.zserv.maps = maps
        self.zserv.max_lost_souls = max_lost_souls
        self.zserv.max_clients = max_clients
        self.zserv.max_clients_per_ip = max_clients_per_ip
        self.zserv.max_players = max_players
        self.zserv.max_players_per_team = max_players_per_team
        self.zserv.max_teams = max_teams
        self.zserv.min_players = min_players
        self.zserv.motd = motd
        self.zserv.nice_weapons = nice_weapons
        self.zserv.no_file_compression = no_file_compression
        self.zserv.no_team_starts = no_team_starts
        self.zserv.no_armor = no_armor
        self.zserv.no_crosshair = no_crosshair
        self.zserv.no_exit = no_exit
        self.zserv.no_exit_kill = no_exit_kill
        self.zserv.no_freelook = no_freelook
        self.zserv.no_health = no_health
        self.zserv.no_items = no_items
        self.zserv.no_jump = no_jump
        self.zserv.no_monsters = no_monsters
        self.zserv.no_passover = no_passover
        self.zserv.no_super = no_super
        self.zserv.old_ctf_convention = old_ctf_convention
        self.zserv.old_falling_damage = old_falling_damage
        self.zserv.old_jump = old_jump
        self.zserv.old_player_movement = old_player_movement
        self.zserv.old_random = old_random
        self.zserv.old_sound_cutoff = old_sound_cutoff
        self.zserv.old_wallrun = old_wallrun
        self.zserv.old_weapon_switch = old_weapon_switch
        self.zserv.old_weapon_sounds = old_weapon_sounds
        self.zserv.optional_wads = optional_wads
        self.zserv.overtime = overtime
        self.zserv.playing_colors = playing_colors
        self.zserv.powerful_monsters = powerful_monsters
        self.zserv.quad_respawn_time = quad_respawn_time
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
        self.zserv.remove_bots_when_humans = remove_bots_when_humans
        self.zserv.requires_password = requires_password
        self.zserv.resend_lost_packets = resend_lost_packets
        self.zserv.reset_inventory = reset_inventory
        self.zserv.respawn_barrels = respawn_barrels
        self.zserv.respawn_items = respawn_items
        self.zserv.respawn_monsters = respawn_monsters
        self.zserv.respawn_protection = respawn_protection
        self.zserv.respawn_super_items = respawn_super_items
        self.zserv.restart_empty_map = restart_empty_map
        self.zserv.same_level = same_level
        self.zserv.same_spawn_spot = same_spawn_spot
        self.zserv.score_limit = score_limit
        self.zserv.server_password = server_password
        self.zserv.show_killing_sprees = show_killing_sprees
        self.zserv.show_multi_kills = show_multi_kills
        self.zserv.silent_bfg = silent_bfg
        self.zserv.skill = skill
        self.zserv.spam_limit = spam_limit
        self.zserv.spam_window = spam_window
        self.zserv.spawn_farthest = spawn_farthest
        self.zserv.specs_dont_disturb_players = specs_dont_disturb_players
        self.zserv.speed_check = speed_check
        self.zserv.splash_factor = splash_factor
        self.zserv.strong_monsters = strong_monsters
        self.zserv.team_autoaim = team_autoaim
        self.zserv.team_color_instances = team_color_instances
        self.zserv.team_damage = team_damage
        self.zserv.team_keys = team_keys
        self.zserv.telemissiles = telemissiles
        self.zserv.time_limit = time_limit
        self.zserv.unlagged = unlagged
        self.zserv.use_blocking = use_blocking
        self.zserv.vampire_mode = vampire_mode
        self.zserv.voodoo_spawns = voodoo_spawns
        self.zserv.var_friction = var_friction
        self.zserv.var_pushers = var_friction
        self.zserv.weapons_stay = weapons_stay
        self.zserv.website = website
        self.zserv.vote_limit = vote_limit
        self.zserv.vote_timeout = vote_timeout
        self.zserv.minimum_vote_percent = minimum_vote_percent
        self.zserv.kick_voting = kick_voting
        self.zserv.kick_vote_percent = kick_vote_percent
        self.zserv.map_voting = map_voting
        self.zserv.random_map_voting = random_map_voting
        self.zserv.skip_map_voting = skip_map_voting
        self.zserv.map_reset_voting = map_reset_voting
        self.zserv.map_vote_percent = map_vote_percent
        self.zserv.random_captain_voting = random_captain_voting
        ###
        # Stuff added in 1.09 (and maybe 1.08.08 RCs
        #   sv_specteamblock
        #   sv_oldthrust
        #   sv_allowzoom
        #   item_respawn_time
        #   cl_interp (0 is equivalent to sv_fineticks 1.08) 0 - 5
        #
        #   sv_fineticks is replaced (sorta) by cl_updatemod:
        #
        #   1: updates all positions on every tick: best accuracy, but also
        #      highest bandwith -- equivalent to sv_fineticks "1"
        #   2: updates all positions every 2 ticks: medium accuracy, lower
        #      bandwidth
        #   3: updates all postions every 3 ticks: lower accuracy, lowest
        #      bandwidth 
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
        def add_bool_line(bool, zs_option_name):
            line = 'set %s "%%s"' % (zs_option_name)
            if bool:
                line = line % ('1')
            else:
                line = line % ('0')
            if add_line(True, line):
                return bool
            return False
        def add_var_line(var, zs_option_name):
            line = 'set %s "%%s"' % (zs_option_name)
            return add_line(var, line % (var))
        add_line(True, 'set cfg_activated "1"')
        ###
        # 0: old logs are left in self.zserv.home_folder.
        # 1: old logs are moved to self.zserv.home_folder/old-logs.
        # 2: old logs are deleted.
        ###
        add_line(True, 'set log_disposition "2"')
        # if self.zserv.use_global_banlist:
        #     addr = (self.zserv.zdstack.hostname, self.zserv.zdstack.port)
        #     banlist_url = 'http://%s:%s/bans' % addr
        #     add_var_line(banlist_url, 'set banlist_url "%s"')
        add_bool_line(self.zserv.add_rocket_explosion, 'addrocketexplosion')
        add_var_line(self.zserv.admin_email, 'email')
        add_bool_line(self.zserv.advertise, 'master_advertise')
        add_var_line(self.zserv.air_control, 'sv_aircontrol')
        add_bool_line(self.zserv.allow_target_names, 'sv_allow_target_names')
        add_var_line(self.zserv.alternate_wads, 'setaltwads')
        # add_var_line(self.zserv.banlist_url, 'banlist_url')
        add_var_line(self.zserv.death_limit, 'sv_deathlimit')
        add_var_line(self.zserv.developer, 'developer')
        add_var_line(self.zserv.dmflags, 'dmflags')
        add_var_line(self.zserv.dmflags2, 'dmflags2')
        add_bool_line(self.zserv.drop_weapons, 'sv_weapondrop')
        add_bool_line(self.zserv.falling_damage, 'sv_falldamage')
        add_bool_line(self.zserv.fast_monsters, 'sv_fastmonsters')
        add_bool_line(self.zserv.fineticks, 'sv_fineticks')
        add_bool_line(self.zserv.force_respawn, 'sv_forcerespawn')
        add_bool_line(self.zserv.force_water, 'forcewater')
        add_var_line(self.zserv.frag_limit, 'fraglimit')
        add_bool_line(self.zserv.generate_block_map, 'genblockmap')
        add_var_line(self.zserv.gravity, 'gravity')
        add_var_line(self.zserv.heapsize, 'heapsize')
        add_bool_line(self.zserv.hide_countries, 'sv_hide_countries')
        add_var_line(self.zserv.hostname, 'hostname')
        add_bool_line(self.zserv.infinite_ammo, 'sv_infiniteammo')
        add_bool_line(self.zserv.instant_weapon_switching, 'sv_insta_switch')
        add_bool_line(self.zserv.keep_keys, 'sv_keepkeys')
        add_bool_line(self.zserv.keys_in_team_modes, 'sv_keys_inteammodes')
        add_bool_line(self.zserv.keys_stay, 'sv_keys_stay')
        add_var_line(self.zserv.kill_limit, 'killlimit')
        add_bool_line(self.zserv.log_sent_packets, 'sv_unlag_report')
        add_var_line(self.zserv.max_lost_souls, 'maxlostsouls')
        add_var_line(self.zserv.max_clients, 'maxclients')
        add_var_line(self.zserv.max_clients_per_ip, 'sv_maxclientsperip')
        add_var_line(self.zserv.max_players, 'maxplayers')
        add_var_line(self.zserv.max_players_per_team, 'maxplayersperteam')
        add_var_line(self.zserv.max_teams, 'maxteams')
        add_var_line(self.zserv.min_players, 'minplayers')
        add_var_line(self.zserv.motd, 'motd')
        add_bool_line(self.zserv.nice_weapons, 'sv_niceweapons')
        add_bool_line(self.zserv.no_file_compression, 'nofilecompression')
        add_bool_line(self.zserv.no_team_starts, 'sv_no_team_starts')
        add_bool_line(self.zserv.no_armor, 'sv_noarmor')
        add_bool_line(self.zserv.no_crosshair, 'sv_nocrosshair')
        add_bool_line(self.zserv.no_exit, 'sv_noexit')
        add_bool_line(self.zserv.no_exit_kill, 'sv_noexitkill')
        add_bool_line(self.zserv.no_freelook, 'sv_nofreelook')
        add_bool_line(self.zserv.no_health, 'sv_nohealth')
        add_bool_line(self.zserv.no_items, 'sv_noitems')
        add_bool_line(self.zserv.no_jump, 'sv_nojump')
        add_bool_line(self.zserv.no_monsters, 'sv_nomonsters')
        add_bool_line(self.zserv.no_passover, 'sv_nopassover')
        add_bool_line(self.zserv.no_super, 'sv_nosuper')
        add_bool_line(self.zserv.old_ctf_convention, 'sv_ctf_old_convention')
        add_bool_line(self.zserv.old_falling_damage, 'sv_oldfalldamage')
        add_bool_line(self.zserv.old_jump, 'sv_oldjump')
        add_bool_line(self.zserv.old_player_movement, 'sv_oldpmovement')
        add_bool_line(self.zserv.old_random, 'sv_oldrandom')
        add_bool_line(self.zserv.old_sound_cutoff, 'sv_oldsoundcut')
        add_bool_line(self.zserv.old_wallrun, 'sv_oldwallrun')
        add_bool_line(self.zserv.old_weapon_switch, 'sv_oldweaponswitch')
        add_bool_line(self.zserv.old_weapon_sounds, 'sv_oldwepsounds')
        add_var_line(self.zserv.optional_wads, 'optional_wads')
        add_bool_line(self.zserv.overtime, 'overtime')
        add_bool_line(self.zserv.powerful_monsters, 'sv_powerful_monsters')
        add_bool_line(self.zserv.quad_respawn_time, 'sv_quadrespawntime')
        if add_bool_line(self.zserv.rcon_enabled, 'enable_rcon'):
            add_var_line(self.zserv.rcon_password, 'rcon_password')
        if self.zserv.rcon_password_1 and self.zserv.rcon_commands_1:
            add_var_line(self.zserv.rcon_password_1, 'rcon_pwd_1')
            add_var_line(' '.join(self.zserv.rcon_commands_1), 'rcon_cmds_1')
        if self.zserv.rcon_password_2 and self.zserv.rcon_commands_2:
            add_var_line(self.zserv.rcon_password_2, 'rcon_pwd_2')
            add_var_line(' '.join(self.zserv.rcon_commands_2), 'rcon_cmds_2')
        if self.zserv.rcon_password_3 and self.zserv.rcon_commands_3:
            add_var_line(self.zserv.rcon_password_3, 'rcon_pwd_3')
            add_var_line(' '.join(self.zserv.rcon_commands_3), 'rcon_cmds_3')
        if self.zserv.rcon_password_4 and self.zserv.rcon_commands_4:
            add_var_line(self.zserv.rcon_password_4, 'rcon_pwd_4')
            add_var_line(' '.join(self.zserv.rcon_commands_4), 'rcon_cmds_4')
        if self.zserv.rcon_password_5 and self.zserv.rcon_commands_5:
            add_var_line(self.zserv.rcon_password_5, 'rcon_pwd_5')
            add_var_line(' '.join(self.zserv.rcon_commands_5), 'rcon_cmds_5')
        if self.zserv.rcon_password_6 and self.zserv.rcon_commands_6:
            add_var_line(self.zserv.rcon_password_6, 'rcon_pwd_6')
            add_var_line(' '.join(self.zserv.rcon_commands_6), 'rcon_cmds_6')
        if self.zserv.rcon_password_7 and self.zserv.rcon_commands_7:
            add_var_line(self.zserv.rcon_password_7, 'rcon_pwd_7')
            add_var_line(' '.join(self.zserv.rcon_commands_7), 'rcon_cmds_7')
        if self.zserv.rcon_password_8 and self.zserv.rcon_commands_8:
            add_var_line(self.zserv.rcon_password_8, 'rcon_pwd_8')
            add_var_line(' '.join(self.zserv.rcon_commands_8), 'rcon_cmds_8')
        if self.zserv.rcon_password_9 and self.zserv.rcon_commands_9:
            add_var_line(self.zserv.rcon_password_9, 'rcon_pwd_9')
            add_var_line(' '.join(self.zserv.rcon_commands_9), 'rcon_cmds_9')
        if add_bool_line(self.zserv.requires_password, 'force_password'):
            add_var_line(self.zserv.server_password, 'password')
        add_var_line(self.zserv.remove_bots_when_humans, 'removebotswhenhumans')
        add_bool_line(self.zserv.resend_lost_packets, 'sv_resend')
        add_bool_line(self.zserv.reset_inventory, 'sv_resetinventory')
        add_bool_line(self.zserv.respawn_barrels, 'sv_barrelrespawn')
        add_bool_line(self.zserv.respawn_items, 'sv_itemrespawn')
        add_bool_line(self.zserv.respawn_monsters, 'sv_monsterrespawn')
        add_bool_line(self.zserv.respawn_protection, 'sv_respawnprotect')
        add_bool_line(self.zserv.respawn_super_items, 'sv_respawnsuper')
        add_bool_line(self.zserv.restart_empty_map, 'restartemptymap')
        add_bool_line(self.zserv.same_level, 'sv_samelevel')
        add_bool_line(self.zserv.same_spawn_spot, 'sv_samespawnspot')
        add_bool_line(self.zserv.show_killing_sprees, 'sv_showsprees')
        add_bool_line(self.zserv.show_multi_kills, 'sv_showmultikills')
        add_bool_line(self.zserv.silent_bfg, 'sv_silentbfg')
        add_var_line(self.zserv.skill, 'skill')
        add_var_line(self.zserv.spam_limit, 'spam_limit')
        add_var_line(self.zserv.spam_window, 'spam_window')
        add_bool_line(self.zserv.spawn_farthest, 'sv_spawnfarthest')
        add_bool_line(self.zserv.specs_dont_disturb_players,
                      'specs_dont_disturb_players')
        add_bool_line(self.zserv.speed_check, 'speed_check')
        add_var_line(self.zserv.splash_factor, 'sv_splashfactor')
        add_bool_line(self.zserv.strong_monsters, 'sv_strong_monsters')
        add_bool_line(self.zserv.team_autoaim, 'sv_teamautoaim')
        add_var_line(self.zserv.team_damage, 'teamdamage')
        add_bool_line(self.zserv.team_keys, 'sv_keys_teamkeys')
        add_bool_line(self.zserv.telemissiles, 'sv_telemissiles')
        add_var_line(self.zserv.time_limit, 'timelimit')
        add_bool_line(self.zserv.unlagged, 'sv_unlag')
        add_bool_line(self.zserv.use_blocking, 'sv_useblocking')
        add_bool_line(self.zserv.vampire_mode, 'sv_vampire')
        add_bool_line(self.zserv.voodoo_spawns, 'sv_voodoo_spawns')
        add_bool_line(self.zserv.var_friction, 'var_friction')
        add_bool_line(self.zserv.var_pushers, 'var_pushers')
        add_bool_line(self.zserv.weapons_stay, 'sv_weaponstay')
        add_bool_line(self.zserv.website, 'website')
        add_var_line(self.zserv.vote_limit, 'sv_vote_limit')
        add_var_line(self.zserv.vote_timeout, 'sv_vote_timeout')
        add_var_line(self.zserv.minimum_vote_percent,
                     'sv_vote_min_participation')
        add_bool_line(self.zserv.kick_voting, 'sv_vote_kick')
        add_var_line(self.zserv.kick_vote_percent, 'sv_vote_kick_percent')
        add_bool_line(self.zserv.map_voting, 'sv_vote_map')
        add_bool_line(self.zserv.random_map_voting, 'sv_vote_randmaps')
        add_bool_line(self.zserv.skip_map_voting, 'sv_vote_map_skip')
        add_bool_line(self.zserv.map_reset_voting, 'sv_vote_reset')
        add_var_line(self.zserv.map_vote_percent, 'sv_vote_map_percent')
        add_bool_line(self.zserv.random_captain_voting, 'sv_vote_randcaps')
        add_bool_line(self.zserv.game_mode in DM_MODES, 'deathmatch')
        if add_bool_line(self.zserv.game_mode in TEAM_MODES, 'teamplay'):
            add_var_line(self.zserv.score_limit, 'teamscorelimit')
        add_bool_line(self.zserv.game_mode in CTF_MODES, 'ctf')
        if self.zserv.maps:
            for map in self.zserv.maps:
                add_line(True, 'addmap %s' % (map))
        if self.zserv.optional_wads:
            add_var_line(' '.join(self.zserv.optional_wads),
                         'optional_wads')
        if self.zserv.alternate_wads:
            y = ' '.join(['='.join(x) for x in self.zserv.alternate_wads])
            add_var_line(y, 'setaltwads')
        cvar_t = 'add_cvaroverride %%s %s'
        ###
        # if self.zserv.overtime:
        #     over_t = cvar_t % ('overtime 1')
        # else:
        #     over_t = cvar_t % ('overtime 0')
        if self.zserv.add_mapnum_to_hostname:
            s = 'hostname "%s - %%s"' % (self.zserv.hostname)
            host_t = cvar_t % (s)
        for map in self.zserv.maps:
            # add_var_line(map, over_t)
            if self.zserv.add_mapnum_to_hostname:
                add_line(True, host_t % (map, map.upper()))
        return self._new_template

