from __future__ import with_statement

import os
import time
import select
import logging

from decimal import Decimal
from datetime import date, datetime, timedelta
from threading import Timer, Lock
from collections import deque
from subprocess import Popen, PIPE, STDOUT

from elixir import session # is this threadsafe?  who cares, we're INSAAAANE!

from pyfileutils import write_file

from ZDStack import ZDSThreadPool
from ZDStack import DEVNULL, DEBUGGING, DIE_THREADS_DIE, TEAM_COLORS, \
                    PlayerNotFoundError, get_session
from ZDStack.Utils import yes, no, to_list
from ZDStack.LogFile import LogFile
from ZDStack.ZDSModels import get_port, get_game_mode, get_map, Round
from ZDStack.LogParser import GeneralLogParser
from ZDStack.LogListener import GeneralLogListener, PluginLogListener
from ZDStack.ZDSTeamsList import TeamsList
from ZDStack.ZDSPlayersList import PlayersList

COOP_MODES = ('coop', 'cooperative', 'co-op', 'co-operative')
DUEL_MODES = ('1v1', 'duel', '1vs1')
FFA_MODES = ('ffa', 'deathmatch', 'dm', 'free for all', 'free-for-all')
TEAMDM_MODES = ('teamdm', 'team deathmatch', 'tdm')
CTF_MODES = ('ctf', 'capture the flag', 'capture-the-flag')

DM_MODES = DUEL_MODES + FFA_MODES + TEAMDM_MODES + CTF_MODES
TEAM_MODES = TEAMDM_MODES + CTF_MODES

class ZServ:

    """ZServ provides an interface to a zserv process.

    ZServ does the following:

      * Handles configuration of the zserv process
      * Provides control over the zserv process
      * Provides a method to communicate with the zserv process
      * Exports server configuration information

    """

    source_port = get_port(name='zdaemon')

    ###
    # There might still be race conditions here
    # TODO: explicitly go through each method and check for thread-safety,
    #       especially in RPC-accessible methods & the data structures they
    #       use.
    ###

    def __init__(self, name, config, zdstack):
        """Initializes a ZServ instance.

        name:      a string representing the name of this ZServ.
        config:    a dict of configuration values for this ZServ.
        zdstack:   the calling (ZD)Stack instance.

        """
        self.start_time = datetime.now()
        self.name = name
        self.session_lock = Lock()
        self.to_save = deque()
        self.game_mode = None
        self.zdstack = zdstack
        self.keep_spawning = False
        self._zserv_stdin_lock = Lock()
        self.map = None
        self.round = None
        self.players = PlayersList(self)
        self.teams = TeamsList(self)
        self._template = ''
        self.reload_config(config)
        self.initialize_session()
        self.zserv = None
        self.fifo = None
        self.logfile = LogFile(GeneralLogParser(), self)
        self.plugins = []
        if self.events_enabled:
            self.logfile.listeners.append(GeneralLogListener(self))
            if self.plugins_enabled and \
              ('plugins' in self.config and self.config['plugins']):
                logging.info("Loading plugins")
                plugins = [x.strip() for x in self.config['plugins'].split(',')]
                self.plugins = plugins
                for plugin in self.plugins:
                    logging.info("Loaded plugin [%s]" % (plugin))
                self.logfile.listeners.append(PluginLogListener(self))
            else:
                logging.info("Not loading plugins")
                logging.debug("Plugins: [%s]" % ('plugins' in self.config))
            logging.debug("Listeners: [%s]" % (self.logfile.listeners))

    def initialize_session(self):
        """Initializes the SQLAlchemy session.
        
        game_mode:    a string representing the game mode of this
                      ZServ.
        acquire_lock: a boolean that, if True, acquires the session
                      lock before initializing the session.  True by
                      default.
        
        """
        logging.debug("Initializing session")
        has_teams = self.raw_game_mode in TEAM_MODES
        self.game_mode = get_game_mode(name=self.raw_game_mode,
                                       has_teams=has_teams)

    ###
    # I have to say that I'm very close to pulling all the config stuff out
    # into separate classes.  Over 400 lines of code is more than 30% of
    # ZServ, and it's not even the main point of the class.  I will do it in a
    # later commit I think.
    #
    # TODO: Move all config stuff into separate classes.
    #
    ###

    def reload_config(self, config):
        """Reloads the config for the ZServ.

        config: a dict of configuration options and values.

        """
        logging.debug('')
        self.load_config(config)
        self.configuration = self.get_configuration()
        write_file(self.configuration, self.configfile, overwrite=True)

    def load_config(self, config):
        """Loads this ZServ's config.

        config: a dict of configuration options and values.

        """
        logging.debug('')
        def is_valid(x):
            return x in config and config[x]
        def is_yes(x):
            return x in config and yes(config[x])
        ###
        # We absolutely have to set the game mode of this ZServ now.
        ###
        self.raw_game_mode = config['mode']
        def set_value(y, to_exec, should_set=None):
            if should_set is None:
                should_set = lambda y: True
            mode_option = '_'.join([self.raw_game_mode, y])
            if is_valid(mode_option) and should_set(mode_option):
                x = config[mode_option]
                exec to_exec in globals(), locals()
                return True
            elif is_valid(y) and should_set(y):
                x = config[y]
                exec to_exec in globals(), locals()
                return True
            return False
        def set_yes_value(option, to_exec):
            return set_value(option, to_exec, is_yes)
        ### mandatory stuff
        self.wads = []
        if 'wads' in config and config['wads']:
            wads = [x.strip() for x in config['wads'].split(',')]
            for wad in wads:
                wadpath = os.path.join(config['zdstack_wad_folder'], wad)
                if not os.path.isfile(wadpath):
                    es = "%s: WAD [%s] not found"
                    raise ValueError(es % (self.name, wadpath))
            self.wads = wads
        self.homedir = os.path.join(config['zdstack_zserv_folder'], self.name)
        if not os.path.isdir(self.homedir):
            os.mkdir(self.homedir)
        self.fifo_path = os.path.join(self.homedir, 'zdsfifo')
        if os.path.exists(self.fifo_path):
            ###
            # Re-create the FIFO so we know there's no mode problems,
            # and that it's definitely a FIFO.
            ###
            if os.path.isdir(self.fifo_path):
                es = "[%s]: FIFO [%s] cannot be created, a folder with the"
                es += " same name already exists"
                raise Exception(es % (self.name, self.fifo_path))
            else:
                os.remove(self.fifo_path)
        os.mkfifo(self.fifo_path)
        self.iwaddir = config['zdstack_iwad_folder']
        self.waddir = config['zdstack_wad_folder']
        self.base_iwad = config['iwad']
        self.iwad = os.path.join(self.iwaddir, self.base_iwad)
        self.port = int(config['port'])
        self.configfile = os.path.join(self.homedir, self.name + '.cfg')
        self.cmd = [config['zserv_exe'], '-cfg', self.configfile, '-waddir',
                    self.waddir, '-iwad', self.iwad, '-port', str(self.port),
                    '-log']
        for wad in self.wads:
            self.cmd.extend(['-file', wad])
        if 'ip' in config and config['ip']:
            ip = str(config['ip'])
            tokens = ip.split('.')
            if not len(tokens) == 4:
                raise ValueError("Malformed IP Address")
            try:
                int_tokens = [int(t) for t in tokens]
            except:
                raise ValueError("Malformed IP Address")
            for t in int_tokens:
                if t < 0 or t > 255:
                    raise ValueError("Malformed IP Address")
            if tokens[3] == 0 or tokens[3] == 255:
                es = "Cannot advertise a broadcast IP address to master"
                raise ValueError(es)
            if tokens[0] == 10 or \
               (tokens[0] == 172 and tokens[1] in range(16, 32)) or \
               (tokens[0] == 192 and tokens[1] == 168):
                 es = "Cannot advertise a private IP address to master"
                 raise ValueError(es)
            self.cmd.extend(['-ip', ip])
        ### other mandatory stuff
        if is_yes('enable_events'):
            events_enabled = True
        else:
            events_enabled = False
        if is_yes('enable_stats'):
            stats_enabled = True
        else:
            stats_enabled = False
        if is_yes('enable_plugins'):
            plugins_enabled = True
        else:
            plugins_enabled = False
        if not events_enabled:
            if stats_enabled:
                es = "Statistics require events, but they have been disabled"
                raise ValueError(es)
            if plugins_enabled:
                es = "Plugins require events, but they have been disabled"
                raise ValueError(es)
        self.events_enabled = events_enabled
        self.stats_enabled = stats_enabled
        self.plugins_enabled = plugins_enabled
        ### admin stuff
        self.rcon_enabled = None
        self.rcon_password = None
        self.requires_password = None
        self.server_password = None
        self.deathlimit = None
        self.spam_window = None
        self.spam_limit = None
        self.speed_check = None
        self.restart_empty_map = None
        self.rcon_password_1 = None
        self.rcon_commands_1 = None
        self.rcon_password_2 = None
        self.rcon_commands_2 = None
        self.rcon_password_3 = None
        self.rcon_commands_3 = None
        self.rcon_password_4 = None
        self.rcon_commands_4 = None
        self.rcon_password_5 = None
        self.rcon_commands_5 = None
        self.rcon_password_6 = None
        self.rcon_commands_6 = None
        self.rcon_password_7 = None
        self.rcon_commands_7 = None
        self.rcon_password_8 = None
        self.rcon_commands_8 = None
        self.rcon_password_9 = None
        self.rcon_commands_9 = None
        ### voting stuff
        self.vote_limit = None
        self.vote_timeout = None
        self.vote_reset = None
        self.vote_map = None
        self.vote_map_percent = None
        self.vote_map_skip = None
        self.vote_kick = None
        self.vote_kick_percent = None
        ### advertise stuff
        self.admin_email = None
        self.advertise = None
        self.hostname = None
        self.website = None
        self.motd = None
        self.add_mapnum_to_hostname = None
        ### config stuff
        ## game-mode-agnostic stuff
        self.remove_bots_when_humans = None
        self.maps = None
        self.optional_wads = None
        self.alternate_wads = None
        self.overtime = None
        self.skill = None
        self.gravity = None
        self.air_control = None
        self.telemissiles = None
        self.specs_dont_disturb_players = None
        self.min_players = None
        ## game-mode-specific stuff
        self.dmflags = None
        self.dmflags2 = None
        self.playing_colors = None
        self.max_teams = None
        self.max_clients = None
        self.max_players = None
        self.max_players_per_team = None
        self.teamdamage = None
        self.timelimit = None
        self.fraglimit = None
        self.scorelimit = None
        self.auto_respawn = None
        ### Load admin stuff
        if set_value('rcon_password', 'self.rcon_password = x'):
            self.rcon_enabled = True
            if is_valid('rcon_password_1') and is_valid('rcon_commands_1'):
                self.rcon_password_1 = config['rcon_password_1']
                self.rcon_commands_1 = config['rcon_commands_1'].split()
            if is_valid('rcon_password_2') and is_valid('rcon_commands_2'):
                self.rcon_password_2 = config['rcon_password_2']
                self.rcon_commands_2 = config['rcon_commands_2'].split()
            if is_valid('rcon_password_3') and is_valid('rcon_commands_3'):
                self.rcon_password_3 = config['rcon_password_3']
                self.rcon_commands_3 = config['rcon_commands_3'].split()
            if is_valid('rcon_password_4') and is_valid('rcon_commands_4'):
                self.rcon_password_4 = config['rcon_password_4']
                self.rcon_commands_4 = config['rcon_commands_4'].split()
            if is_valid('rcon_password_5') and is_valid('rcon_commands_5'):
                self.rcon_password_5 = config['rcon_password_5']
                self.rcon_commands_5 = config['rcon_commands_5'].split()
            if is_valid('rcon_password_6') and is_valid('rcon_commands_6'):
                self.rcon_password_6 = config['rcon_password_6']
                self.rcon_commands_6 = config['rcon_commands_6'].split()
            if is_valid('rcon_password_7') and is_valid('rcon_commands_7'):
                self.rcon_password_7 = config['rcon_password_7']
                self.rcon_commands_7 = config['rcon_commands_7'].split()
            if is_valid('rcon_password_8') and is_valid('rcon_commands_8'):
                self.rcon_password_8 = config['rcon_password_8']
                self.rcon_commands_8 = config['rcon_commands_8'].split()
            if is_valid('rcon_password_9') and is_valid('rcon_commands_9'):
                self.rcon_password_9 = config['rcon_password_9']
                self.rcon_commands_9 = config['rcon_commands_9'].split()
        if set_value('server_password', 'self.server_password = x'):
            self.requires_password = True
        set_value('deathlimit', 'self.deathlimit = int(x)')
        set_value('spam_window', 'self.spam_window = int(x)')
        set_value('spam_limit', 'self.spam_limit = int(x)')
        set_value('speed_check', 'self.speed_check = True')
        set_value('restart_empty_map', 'self.restart_empty_map = True')
        ### Load voting stuff
        set_value('vote_limit', 'self.vote_limit = int(x)')
        set_value('vote_timeout', 'self.vote_timeout = int(x)')
        set_yes_value('vote_reset', 'self.vote_reset = True')
        if set_yes_value('vote_map', 'self.vote_map = True'):
            if is_valid('vote_map_percent'):
                pc = Decimal(config['vote_map_percent'])
                if pc < 1:
                    pc = pc * Decimal(100)
                self.vote_map_percent = pc
            set_yes_value('vote_map_skip', 'self.vote_map_skip = int(x)')
        if set_yes_value('vote_kick', 'self.vote_kick = True'):
            set_value('vote_kick_percent',
                      'self.vote_kick_percent = Decimal(x)')
        ### Load advertise stuff
        set_value('admin_email', 'self.admin_email = x')
        set_yes_value('advertise', 'self.advertise = True')
        set_value('hostname', 'self.hostname = x')
        set_value('website', 'self.website = x')
        set_value('motd', 'self.motd = x')
        set_yes_value('add_mapnum_to_hostname',
                      'self.add_mapnum_to_hostname = True')
        ### Load game-mode-agnostic config stuff
        set_yes_value('remove_bots_when_humans',
                      'self.remove_bots_when_humans = True')
        set_value('maps', 'self.maps = to_list(x, ",")')
        set_value('optional_wads',
                  'self.optional_wads = to_list(x, ",")')
        set_value('alternate_wads',
            'self.alternate_wads = [y.split("=") for y in x.split()]')
        set_yes_value('overtime', 'self.overtime = True')
        set_value('skill', 'self.skill = int(x)')
        set_value('gravity', 'self.gravity = Decimal(x)')
        set_value('air_control', 'self.air_control = Decimal(x)')
        set_yes_value('telemissiles', 'self.telemissiles = True')
        set_yes_value('specs_dont_disturb_players',
                      'self.specs_dont_disturb_players = True')
        set_value('min_players', 'self.min_players = int(x)')
        set_value('dmflags', 'self.dmflags = x')
        set_value('dmflags2', 'self.dmflags2 = x')
        set_value('max_clients', 'self.max_clients = int(x)')
        if self.raw_game_mode in DUEL_MODES:
            self.max_players = 2
        else:
            set_value('max_players', 'self.max_players = int(x)')
        set_value('timelimit', 'self.timelimit = int(x)')
        set_value('auto_respawn', 'self.auto_respawn = int(x)')
        set_value('teamdamage', 'self.teamdamage = Decimal(x)')
        if set_value('max_teams', 'self.max_teams = int(x)'):
            self.playing_colors = TEAM_COLORS[:self.max_teams]
        set_value('max_players_per_team',
                  'self.max_players_per_team = int(x)')
        if self.raw_game_mode in TEAM_MODES:
            set_value('team_score_limit', 'self.scorelimit = int(x)')
        ###
        # Why are we doing this...?  Commenting out to see what breaks :)
        #
        # Oh, it's because previously these were the game-mode specific things
        # that the config parsing supported.  Hmm..., still leaving this
        # disabled for now, because it is dumb to do it this way.
        #
        # config['name'] = self.name
        # config['dmflags'] = self.dmflags
        # config['dmflags2'] = self.dmflags2
        # config['max_clients'] = self.max_clients
        # config['max_players'] = self.max_players
        # config['timelimit'] = self.timelimit
        #
        ###
        self.config = config

    def __str__(self):
        return "<ZServ [%s:%d]>" % (self.name, self.port)

    def get_configuration(self):
        # logging.debug('')
        ###
        # TODO: add support for "add_mapnum_to_hostname"
        ###
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
        # 0: old logs are left in self.homedir.
        # 1: old logs are moved to self.homedir/old-logs.
        # 2: old logs are deleted.
        ###
        add_line(True, 'set log_disposition "2"')
        add_var_line(self.hostname, 'set hostname "%s"')
        add_var_line(self.motd, 'set motd "%s"')
        add_var_line(self.website, 'set website "%s"')
        add_var_line(self.admin_email, 'set email "%s"')
        add_bool_line(self.advertise, 'set master_advertise "%s"')
        if add_bool_line(self.rcon_enabled, 'set enable_rcon "%s"'):
            add_var_line(self.rcon_password, 'set rcon_password "%s"')
        if add_bool_line(self.requires_password, 'set force_password "%s"'):
            add_var_line(self.server_password, 'set password "%s"')
        add_var_line(self.deathlimit, 'set sv_deathlimit "%s"')
        add_var_line(self.spam_window, 'set spam_window "%s"')
        add_var_line(self.spam_limit, 'set spam_limit "%s"')
        add_bool_line(self.speed_check, 'set speed_check "%s"')
        add_var_line(self.vote_limit, 'set sv_vote_limit "%s"')
        add_var_line(self.vote_timeout, 'set sv_vote_timeout "%s"')
        add_bool_line(self.vote_reset, 'set sv_vote_reset "%s"')
        add_bool_line(self.vote_map, 'set sv_vote_map "%s"')
        add_var_line(self.vote_map_percent, 'set sv_vote_map_percent "%s"')
        add_var_line(self.vote_map_skip, 'set sv_vote_map_skip "%s"')
        add_var_line(self.vote_kick, 'set sv_vote_kick "%s"')
        add_var_line(self.vote_kick_percent, 'set sv_vote_kick_percent "%s"')
        if self.rcon_password_1 and self.rcon_commands_1:
            add_var_line(self.rcon_password_1, 'set rcon_pwd_1 "%s"')
            add_var_line(' '.join(self.rcon_commands_1), 'set rcon_cmds_1 "%s"')
        if self.rcon_password_2 and self.rcon_commands_2:
            add_var_line(self.rcon_password_2, 'set rcon_pwd_2 "%s"')
            add_var_line(' '.join(self.rcon_commands_2), 'set rcon_cmds_2 "%s"')
        if self.rcon_password_3 and self.rcon_commands_3:
            add_var_line(self.rcon_password_3, 'set rcon_pwd_3 "%s"')
            add_var_line(' '.join(self.rcon_commands_3), 'set rcon_cmds_3 "%s"')
        if self.rcon_password_4 and self.rcon_commands_4:
            add_var_line(self.rcon_password_4, 'set rcon_pwd_4 "%s"')
            add_var_line(' '.join(self.rcon_commands_4), 'set rcon_cmds_4 "%s"')
        if self.rcon_password_5 and self.rcon_commands_5:
            add_var_line(self.rcon_password_5, 'set rcon_pwd_5 "%s"')
            add_var_line(' '.join(self.rcon_commands_5), 'set rcon_cmds_5 "%s"')
        if self.rcon_password_6 and self.rcon_commands_6:
            add_var_line(self.rcon_password_6, 'set rcon_pwd_6 "%s"')
            add_var_line(' '.join(self.rcon_commands_6), 'set rcon_cmds_6 "%s"')
        if self.rcon_password_7 and self.rcon_commands_7:
            add_var_line(self.rcon_password_7, 'set rcon_pwd_7 "%s"')
            add_var_line(' '.join(self.rcon_commands_7), 'set rcon_cmds_7 "%s"')
        if self.rcon_password_8 and self.rcon_commands_8:
            add_var_line(self.rcon_password_8, 'set rcon_pwd_8 "%s"')
            add_var_line(' '.join(self.rcon_commands_8), 'set rcon_cmds_8 "%s"')
        if self.rcon_password_9 and self.rcon_commands_9:
            add_var_line(self.rcon_password_9, 'set rcon_pwd_9 "%s"')
            add_var_line(' '.join(self.rcon_commands_9), 'set rcon_cmds_9 "%s"')
        add_bool_line(self.raw_game_mode in DM_MODES, 'set deathmatch "%s"')
        if add_bool_line(self.raw_game_mode in TEAM_MODES, 'set teamplay "%s"'):
            add_var_line(self.scorelimit, 'set teamscorelimit "%s"')
        add_bool_line(self.raw_game_mode in CTF_MODES, 'set ctf "%s"')
        add_bool_line(self.telemissiles, 'set sv_telemissiles "%s"')
        add_bool_line(self.specs_dont_disturb_players,
                      'set specs_dont_disturb_players "%s"')
        add_bool_line(self.restart_empty_map, 'set restartemptymap "%s"')
        if self.maps:
            for map in self.maps:
                add_var_line(map, 'addmap "%s"')
        if self.optional_wads:
            add_var_line(' '.join(self.optional_wads), 'set optional_wads "%s"')
        if self.alternate_wads:
            add_var_line(' '.join(['='.join(x) for x in self.alternate_wads]),
                         'setaltwads "%s"')
        if self.overtime:
            t = 'add_cvaroverride %s overtime 1'
        else:
            t = 'add_cvaroverride %s overtime 0'
        for map in self.maps:
            add_var_line(map, t)
        add_var_line(self.skill, 'set skill "%s"')
        add_var_line(self.gravity, 'set gravity "%s"')
        add_var_line(self.air_control, 'set sv_aircontrol "%s"')
        add_var_line(self.min_players, 'set minplayers "%s"')
        add_bool_line(self.remove_bots_when_humans,
                      'set removebotswhenhumans "%s"')
        add_var_line(self.dmflags, 'set dmflags "%s"')
        add_var_line(self.dmflags2, 'set dmflags2 "%s"')
        add_var_line(self.max_clients, 'set maxclients "%s"')
        if self.raw_game_mode in DUEL_MODES:
            self.max_players = 2
        add_var_line(self.max_players, 'set maxplayers "%s"')
        add_var_line(self.timelimit, 'set timelimit "%s"')
        add_var_line(self.fraglimit, 'set fraglimit "%s"')
        add_var_line(self.auto_respawn, 'set sv_autorespawn "%s"')
        add_var_line(self.teamdamage, 'set teamdamage "%s"')
        self._template = self._new_template
        return self._template

    def is_running(self):
        """Returns True if the internal zserv process is running."""
        ###
        # If the internal zserv process has exited, it will have a
        # returncode... which we can get with .poll().  Otherwise
        # .poll() returns None.
        ###
        if not self.zserv or not self.zserv.pid:
            return False
        x = self.zserv.poll()
        # logging.debug('Poll: %s' % (x))
        return x is None

    def ensure_loglinks_exist(self):
        """Creates links from all potential logfiles to the FIFO."""
        ###
        # zserv itself will remove old links, so no worries.
        ###
        today = date.today()
        s = 'gen-%Y%m%d.log'
        for loglink_name in [today.strftime(s),
                             (today + timedelta(days=1)).strftime(s),
                             (today + timedelta(days=2)).strftime(s)]:
            loglink_path = os.path.join(self.homedir, loglink_name)
            if not os.path.islink(loglink_path):
                os.symlink(self.fifo_path, loglink_path)

    def spawn_zserv(self):
        """Starts the zserv process.
        
        This keeps a reference to the running zserv process in
        self.zserv.
        
        """
        # logging.debug('Acquiring spawn lock [%s]' % (self.name))
        with self.zdstack.spawn_lock:
            if self.is_running():
                return
            curdir = os.getcwd()
            try:
                os.chdir(self.homedir)
                self.ensure_loglinks_exist()
                logging.info("Spawning zserv [%s]" % (' '.join(self.cmd)))
                ###
                # Should we do something with STDERR here?
                ###
                self.zserv = Popen(self.cmd, stdin=PIPE, stdout=DEVNULL,
                                   stderr=STDOUT, bufsize=0, close_fds=True)
                self.fifo = os.open(self.fifo_path, os.O_RDONLY | os.O_NONBLOCK)
                # self.send_to_zserv('players') # avoids CPU spinning
            finally:
                os.chdir(curdir)

    def start(self):
        """Starts the zserv process, restarting it if it crashes."""
        logging.debug('Starting all listeners')
        if self.is_running():
            raise Exception("[%s] already started" % (self.name))
        self.logfile.start_listeners()
        self.keep_spawning = True
        self.spawning_thread = \
            ZDSThreadPool.get_thread(name='%s spawning thread' % (self.name),
                                     target=self.spawn_zserv,
                                     keep_going=lambda: self.keep_spawning,
                                     sleep=Decimal('.5'))

    def stop(self, signum=15, stop_logfile=True):
        """Stops the zserv process.

        signum:       an int representing the signal number to send to
                      the zserv process.  15 (TERM) by default.
        stop_logfile: a boolean that, if True, will stop the logfile
                      as well.  True by default.

        """
        if not self.is_running():
            raise Exception("[%s] already stopped" % (self.name))
        logging.debug("Setting keep_spawning False")
        self.keep_spawning = False
        logging.debug("Joining spawning thread")
        ZDSThreadPool.join(self.spawning_thread)
        logging.debug("Killing zserv process")
        error_stopping = False
        if self.is_running():
            try:
                os.kill(self.zserv.pid, signum)
                retval = self.zserv.wait()
            except Exception, e:
                es = "Caught exception while stopping: [%s]"
                logging.error(es % (e))
                error_stopping = es % (e)
        if stop_logfile:
            logging.debug('Stopping all listeners')
            self.logfile.stop_listeners()
        return error_stopping

    def restart(self, signum=15):
        """Restarts the zserv process, restarting it if it crashes.

        signum: an int representing the signal number to send to the
                zserv process.  15 (TERM) by default.

        """
        logging.debug('')
        error_stopping = self.stop(signum)
        if error_stopping:
            s = 'Caught exception while stopping: [%s] already stopped'
            if error_stopping != s % (self.name):
                ###
                # If the zserv was already stopped, just start it.  Other errors
                # get raised.
                ###
                raise Exception(error_stopping)
        self.start()

    def sync_players(self, sleep=None):
        """Ensures that self.players matches up with self.zplayers().
        
        sleep: a float representing how much time to sleep between
               acquiring the _players_lock and creating the list of
               players; defaults to not sleeping at all (None)
               
        """
        logging.debug("ZServ.sync_players")
        if sleep:
            with self.players.lock:
                logging.debug("Getting ZPlayers")
                zplayers = self.zplayers()
                time.sleep(sleep)
                logging.debug("self.players.sync(acquire_lock=False")
                self.players.sync(zplayers, acquire_lock=False)
        else:
            logging.debug("self.players.sync(acquire_lock=True")
            self.players.sync(acquire_lock=True)

    def update_player_numbers_and_ips(self):
        """Sets player numbers and IP addresses.

        This method needs to be run upon every connection and
        disconnection if numbers and names are to remain in sync.

        """
        for d in self.zplayers():
            try:
                p = self.players.get(ip_address_and_port=(d['player_ip'],
                                                          d['player_port']))
            except PlayerNotFoundError, pnfe:
                es = "Players out of sync, %s at %s:%s not found"
                logging.debug(es % (d['player_name'], d['player_ip'],
                                    d['player_port']))
                ###
                # Previously, we weren't adding players that weren't found...
                # so if this causes errors it should ostensibly be removed.
                ###
                p = Player(self, d['player_ip'], d['player_port'],
                                 d['player_name'], d['player_num'])
                self.players.add(p)
                continue
            except Exception, e:
                logging.error("Error updating player #s and IPs: %s" % (e))
                continue
            with self.players.lock:
                p.set_name(d['player_name'])
                p.number = d['player_num']
                es = "Set name/number %s/%s to address %s:%s"
                logging.debug(es % (p.name, p.number, p.ip, p.port))
        self.players.sync()

    def distill_player(self, possible_player_names):
        """Discerns the most likely existing player.

        possible_player_names: a list of strings representing possible
                               player names

        Because messages are formatted in such a way that separating
        messenger's name from the message is not straightforward, this
        function will return the most likely player name from a list of
        possible messenger names.  This function has other uses, but
        that's the primary one.

        """
        m = self.players.get_first_matching_player(possible_player_names)
        if not m:
            ###
            # We used to just do a sync here, but update_player_numbers_and_ips
            # covers more possibilities... even though it requires interaction
            # with the zserv.  So if this causes problems, switch back to just
            # using sync.
            #
            # self.players.sync()
            #
            ###
            self.update_player_numbers_and_ips()
        m = self.players.get_first_matching_player(possible_player_names)
        ###
        # Some logging stuff...
        #
        # if not m:
        #     player_names = ', '.join(names)
        #     ppn = ', '.join(possible_player_names)
        #     logging.info("No player could be distilled")
        #     logging.info("Players: [%s]" % (player_names))
        #     logging.info("Possible: [%s]" % (ppn))
        #
        ###
        return m

    def get_player_ip_address(self, player_name):
        """Returns a player's IP address.
        
        player_name: a string representing the name of the player
                     whose IP address is to be returned

        """
        d = [x for x in self.zplayers() if x['player_name'] == player_name]
        if not d:
            raise PlayerNotFoundError(player_name)
        return d[0]['player_ip']

    def get_player_number(self, player_name):
        """Returns a player's number.
        
        player_name: a string representing the name of the player
                     whose number is to be returned
        
        This number is the same as the number indicated by the zserv
        'players' command, useful for kicking and not much else.

        """
        d = [x for x in self.zplayers() if x['player_name'] == player_name]
        if not d:
            raise PlayerNotFoundError(player_name)
        return d[0]['player_num']

    def add_stat(self, stat):
        """Adds a stat model to the internal list of stat models.

        stat: an object to add to the internal list of stat models.

        """

    def change_map(self, map_number, map_name):
        """Handles a map change event.

        map_number: an int representing the number of the new map
        map_name:   a string representing the name of the new map

        """
        logging.debug('Change Map')
        ses = session()
        if self.round:
            self.round.end_time = datetime.now()
            ses.merge(self.round)
            to_delete = self.round.players + self.round.frags + \
                        self.round.flag_touches + self.round.flag_returns + \
                        self.round.rcon_accesses + self.round.rcon_denials + \
                        self.round.rcon_actions + [self.round]
        else:
            to_delete = []
        if to_delete and not self.stats_enabled:
            ###
            # Not everything is deleted.  Some things we want to persist, like
            # weapons, team colors, ports, game modes and maps.  This stuff
            # shouldn't take up too much memory anyway.  The rest of the stuff,
            # like stats and aliases, all that can go out the window.
            ###
            for x in to_delete:
                logging.debug("Deleting %s" % (x))
                ses.delete(x)
            # ses.close()
        # else:
        #     pass
        #     ses.commit()
        self.to_save.clear()
        self.players.clear()
        self.teams.clear()
        self.map = get_map(number=map_number, name=map_name)
        self.round = Round(game_mode=self.game_mode, map=self.map,
                           start_time=datetime.now())

    def send_to_zserv(self, message, event_response_type=None):
        """Sends a message to the running zserv process.

        message:             a string representing the message to send
        event_response_type: a string representing the type of event to
                             wait for in response

        When using this method, keep the following in mind:

          - Your message cannot contain newlines.
          - If event_response_type is None, no response will be
            returned

        This method returns a list of events returned in response.

        """
        # logging.debug('')
        if '\n' in message or '\r' in message:
            es = "Message cannot contain newlines or carriage returns"
            raise ValueError(es)
        logging.debug("Obtaining STDIN lock")
        with self._zserv_stdin_lock:
            logging.debug("Obtained STDIN lock")
            ###
            # zserv's STDIN is (obviously) not threadsafe, so we need to ensure
            # that access to it is limited to 1 thread at a time, which is both
            # writing to it, and waiting for responses from its STDOUT.
            ###
            if self.events_enabled and event_response_type is not None:
                logging.debug("Setting response type")
                self.logfile.set_response_type(event_response_type)
            logging.debug("Writing to STDIN")
            self.zserv.stdin.write(message + '\n')
            self.zserv.stdin.flush()
            if self.events_enabled and event_response_type is not None:
                logging.debug("Getting response")
                response = self.logfile.get_response()
                logging.debug("Send to zserv response: (%s)" % (response))
                return response

    def zaddban(self, ip_address, reason='rofl'):
        """Adds a ban.

        ip_address: a string representing the IP address to ban
        reason:     a string representing the reason for the ban

        """
        # logging.debug('')
        return self.send_to_zserv('addban %s %s' % (ip_address, reason),
                                  'addban_command')

    def zaddtimedban(self, duration, ip_address, reason='rofl'):
        """Adds a ban with an expiration.

        duration:   an integer representing how many minutes the ban
                    should last
        ip_address: a string representing the IP address to ban
        reason:     a string representing the reason for the ban

        """
        self.zaddban(ip_address, reason)
        seconds = duration * 60
        Timer(seconds, self.zkillban, [ip_address]).start()

    def zaddbot(self, bot_name):
        """Adds a bot.

        bot_name: a string representing the name of the bot to add.

        """
        # logging.debug('')
        return self.send_to_zserv('addbot %s' % (bot_name), 'addbot_command')

    def zaddmap(self, map_number):
        """Adds a map to the maplist.

        map_number: an int representing the name of the map to add

        """
        # logging.debug('')
        return self.send_to_zserv('addmap %s' % (map_number))

    def zclearmaplist(self):
        """Clears the maplist."""
        # logging.debug('')
        return self.send_to_zserv('clearmaplist')

    def zget(self, variable_name):
        """Gets a variable.

        variable_name: a string representing the name of the variable
                       to get

        """
        # logging.debug('')
        return self.send_to_zserv('get %s', 'get_command')

    def zkick(self, player_number, reason='rofl'):
        """Kicks a player.

        player_number: an int representing the number of the player to
                       kick
        reason:        a string representing the reason for the kick

        """
        # logging.debug('')
        return self.send_to_zserv('kick %s %s' % (player_number, reason))

    def zkillban(self, ip_address):
        """Removes a ban.

        ip_address: a string representing the IP address to un-ban

        """
        # logging.debug('')
        return self.send_to_zserv('killban %s' % (ip_address))

    def zmap(self, map_number):
        """Changes the current map.

        map_number: an int representing the number of the map to
                    change to

        """
        # logging.debug('')
        return self.send_to_zserv('map %s' % (map_number))

    def zmaplist(self):
        """Gets the maplist.

        Returns a list of strings representing the names of maps in
        the maplist.  An example of one of these strings is: "map01".

        """
        # logging.debug('')
        return self.send_to_zserv('maplist', 'maplist_command')

    def zplayers(self):
        """Returns a list of players in the server."""
        # logging.debug('')
        return self.send_to_zserv('players', 'players_command')

    def zremovebots(self):
        """Removes all bots."""
        # logging.debug('')
        return self.send_to_zserv('removebots')

    def zresetscores(self):
        """Resets all scores."""
        # logging.debug('')
        return self.send_to_zserv('resetscores')

    def zsay(self, message):
        """Sends a message as ] CONSOLE [.
        
        message: a string representing the message to send.
        
        """
        # logging.debug('')
        return self.send_to_zserv('say %s' % (message))

    def zset(self, variable_name, variable_value):
        """Sets a variable.

        variable_name:  a string representing the name of the variable
                        to set
        variable_value: a string representing the value to set the
                        variable to

        """
        # logging.debug('')
        s = 'set "%s" "%s"' % (variable_name, variable_value)
        return self.send_to_zserv(s)

    def ztoggle(self, boolean_variable):
        """Toggles a boolean variable.

        boolean_variable: a string representing the name of the
                          boolean variable to toggle

        """
        # logging.debug('')
        return self.send_to_zserv('toggle %s' % (boolean_variable))

    def zunset(self, variable_name):
        """Unsets a variable.

        variable_name: a string representing the name of the variable
                       to unset

        """
        # logging.debug('')
        return self.send_to_zserv('unset %s' % (variable_name))

    def zwads(self):
        """Returns a list of the wads in use."""
        # logging.debug('')
        return self.send_to_zserv('wads', 'wads_command')

    def export(self):
        """Returns a dict of ZServ configuration information."""
        ###
        # TODO: update this stuff for recent zservs and new config options
        ###
        logging.debug('')
        d = {'name': self.name,
             'mode': self.raw_game_mode,
             'port': self.port,
             'iwad': self.base_iwad,
             'wads': [os.path.basename(x) for x in self.wads],
             'optional_wads': self.optional_wads,
             'maps': self.maps,
             'dmflags': self.dmflags,
             'dmflags2': self.dmflags2,
             'admin_email': self.admin_email,
             'website': self.website.replace('\\', '/'),
             'advertise': self.advertise,
             'hostname': self.hostname,
             'motd': self.motd.replace('<br>', '\n'),
             'remove_bots_when_humans': self.remove_bots_when_humans,
             'overtime': self.overtime,
             'skill': self.skill,
             'gravity': self.gravity,
             'air_control': self.air_control,
             'min_players': self.min_players,
             'max_players': self.max_players,
             'max_clients': self.max_clients,
             'deathlimit': self.deathlimit,
             'timelimit': self.timelimit,
             'fraglimit': self.fraglimit,
             'scorelimit': self.scorelimit,
             'spam_window': self.spam_window,
             'spam_limit': self.spam_limit,
             'speed_check': self.speed_check,
             'restart_empty_map': self.restart_empty_map}
        for func in self.extra_exportables_funcs:
            d = func(d)
        return d

