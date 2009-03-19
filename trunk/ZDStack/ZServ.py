from __future__ import with_statement

import os
import time
import logging

from decimal import Decimal
from datetime import datetime
from threading import Timer, Lock
from subprocess import Popen, PIPE

from pyfileutils import write_file

from ZDStack import HOSTNAME, PlayerNotFoundError
from ZDStack.Utils import yes, no
from ZDStack.LogFile import LogFile
from ZDStack.ZDSModels import Player, Team
from ZDStack.LogParser import GeneralLogParser
from ZDStack.LogListener import GeneralLogListener, PluginLogListener

COOP_TYPES = ('coop', 'cooperative', 'co-op', 'co-operative')
DUEL_TYPES = ('1v1', 'duel')
FFA_TYPES = ('ffa', 'deathmatch', 'dm', 'free for all', 'free-for-all')
TEAMDM_TYPES = ('teamdm', 'team deathmatch', 'tdm')
CTF_TYPES = ('ctf', 'capture the flag', 'capture-the-flag')

DM_TYPES = DUEL_TYPES + FFA_TYPES + TEAMDM_TYPES + CTF_TYPES
TEAM_TYPES = TEAMDM_TYPES + CTF_TYPES

class BaseZServ:

    """BaseZServ represents the base ZServ class.

    BaseZServ does the following:

      * Handles configuration of the zserv process
      * Provides control over the zserv process
      * Provides a method to communicate with the zserv process
      * Exports server configuration information

    """

    # There are probably a lot of race conditions here...
    # TODO: add locks, specifically in RPC-accessible methods and
    #       around the data structures they use.

    def __init__(self, name, type, config, zdstack):
        """Initializes a BaseZServ instance.

        name:    a string representing the name of this ZServ.
        type:    the game-mode of this ZServ, like 'ctf', 'ffa', etc.
        config:  a dict of configuration values for this ZServ.
        zdstack: the calling ZDStack instance

        """
        self.start_time = datetime.now()
        self.name = name
        self.type = type
        self.zdstack = zdstack
        self.keep_spawning = False
        self.already_watching = False
        self._players_lock = Lock()
        self._zserv_stdin_lock = Lock()
        ###
        # Hmm...
        self.players = list()
        self.disconnected_players = list()
        self.teams = list()
        # End Hmm...
        ###
        self.reload_config(config)
        self.zserv = None
        self.pid = None
        self.logfile = LogFile(GeneralLogParser(), self)
        self.plugins = []
        if yes(self.config['enable_events']):
            self.logfile.listeners.append(GeneralLogListener(self))
            if yes(self.config['enable_plugins']) and 'plugins' in self.config:
                logging.info("Loading plugins")
                plugins = [x.strip() for x in self.config['plugins'].split(',')]
                self.plugins = plugins
                for plugin in self.plugins:
                    logging.info("Loaded plugin [%s]" % (plugin))
                self.logfile.listeners.append(PluginLogListener(self))
            else:
                logging.info("Not loading plugins")
                logging.debug("Load plugins: [%s]" % (load_plugins))
                logging.debug("Plugins: [%s]" % ('plugins' in self.config))
            logging.debug("Listeners: [%s]" % (self.logfile.listeners))

    ###
    # I have to say that I'm very close to pulling all the config stuff out
    # into separate classes.  Over 400 lines of code is more than 30% of
    # BaseZServ, and it's not even the main point of the class.  I will do it
    # in a later commit I think.
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
        def set_value(option, parse_func, should_set=None):
            should_set = should_set or lambda x: True
            type_option = '_'.join([self.type, option])
            if is_valid(type_option) and should_set(type_option):
                parse_func(config[type_option])
                return True
            elif is_valid(option) and should_set(option):
                parse_func(option)
                return True
            return False
        def set_yes_value(option, parse_func):
            return set_value(option, parse_func, is_yes)
        def to_list(s, sep):
            return [x for x in s.split(sep) if x]
        ### mandatory stuff
        mandatory_options = \
            ('iwad', 'waddir', 'iwaddir', 'port', 'maps_to_remember',
             'zservfolder', 'enable_events', 'enable_stats', 'enable_plugins')
        for mandatory_option in mandatory_options:
            if mandatory_option not in config:
                es = "%s: Could not find required option '%s' in configuration"
                raise ValueError(es % (self.name, mandatory_option))
        ### CMD-line stuff
        if not os.path.isdir(config['iwaddir']):
            es = "%s: IWAD dir %s is not valid"
            raise ValueError(es % (self.name, config['iwaddir']))
        if not os.path.isdir(config['waddir']):
            es = "%s: WAD dir %s is not valid"
            raise ValueError(es % (self.name, config['waddir']))
        if not os.path.isfile(os.path.join(config['iwaddir'], config['iwad'])):
            es = "%s: Could not find IWAD %s"
            raise ValueError(es % (self.name, config['iwad']))
        if not os.path.isdir(config['zservfolder']):
            try:
                os.mkdir(config['zservfolder'])
            except Exception, e:
                es = "%s: ZServ Server folder %s is not valid: %s"
                raise ValueError(es % (self.name, config['zservfolder'], e))
        self.wads = []
        if 'wads' in config and config['wads']:
            wads = [x.strip() for x in config['wads'].split(',')]
            for wad in wads:
                wadpath = os.path.join(config['waddir'], wad)
                if not os.path.isfile(wadpath):
                    es = "%s: WAD [%s] not found"
                    raise ValueError(es % (self.name, wad))
            self.wads = wads
        self.homedir = os.path.join(config['zservfolder'], self.name)
        if not os.path.isdir(self.homedir):
            os.mkdir(self.homedir)
        self.iwaddir = config['iwaddir']
        self.waddir = config['waddir']
        self.base_iwad = config['iwad']
        self.iwad = os.path.join(self.iwaddir, self.base_iwad)
        self.port = int(config['port'])
        self.maps_to_remember = int(config['maps_to_remember'])
        self.configfile = os.path.join(self.homedir, self.name + '.cfg')
        self.cmd = [config['zserv_exe'], '-waddir', self.waddir, '-iwad',
                    self.iwad, '-port', str(self.port), '-cfg',
                    self.configfile, '-clog', '-log']
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
                es = "Statistics require events, but they have been disabled")
                raise ValueError(es)
            if plugins_enabled:
                es = "Plugins require events, but they have been disabled")
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
        self.vote_map_kick = None
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
        if set_yes_value('enable_rcon', lambda x: self.rcon_enabled = True):
            if set_value('rcon_password', lambda x: self.rcon_password = x):
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
        if set_yes_value('requires_password', \
                         lambda x: self.requires_password = True):
            set_value('server_password', lambda x: self.server_password = x)
        set_value('deathlimit', lambda x: self.deathlimit = int(x))
        set_value('spam_window', lambda x: self.spam_window = int(x))
        set_value('spam_limit', lambda x: self.spam_limit = int(x))
        set_value('speed_check', lambda x: self.speed_check = True)
        set_value('restart_empty_map', lambda x: self.restart_empty_map = True)
        ### Load voting stuff
        set_value('vote_limit', lambda x: self.vote_limit = int(x))
        set_value('vote_timeout', lambda x: self.vote_timeout = int(x))
        set_yes_value('vote_reset', lambda x: self.vote_reset = True)
        if set_yes_value('vote_map', lambda x: self.vote_map = True):
            if is_valid('vote_map_percent'):
                pc = Decimal(config['vote_map_percent'])
                if pc < 1:
                    pc = pc * Decimal(100)
                self.vote_map_percent = pc
            set_yes_value('vote_map_skip',
                          lambda x: self.vote_map_skip = int(x))
        if set_yes_value('vote_map_kick', lambda x: self.vote_map_kick = True):
            set_value('vote_kick_percent',
                      lambda x: self.vote_kick_percent = Decimal(x))
        ### Load advertise stuff
        set_value('admin_email', lambda x: self.admin_email = x)
        set_yes_value('advertise', lambda x: self.advertise = True)
        set_value('hostname', lambda x: self.hostname = x)
        set_value('website', lambda x: self.website = x)
        set_value('motd', lambda x: self.motd = x)
        set_yes_value('add_mapnum_to_hostname',
                      lambda x: self.add_mapnum_to_hostname = True)
        ### Load game-mode-agnostic config stuff
        set_yes_value('remove_bots_when_humans',
                      lambda x: self.remove_bots_when_humans = True)
        set_value('maps', lambda x: self.maps = to_list(x, ','))
        set_value('optional_wads',
                  lambda x: self.optional_wads = to_list(x, ','))
        set_value('alternate_wads',
            lambda x: self.alternate_wads = [y.split('=') for y in x.split()])
        set_yes_value('overtime', lambda x: self.overtime = True)
        set_yes_value('skill', lambda x: self.skill = int(x))
        set_yes_value('gravity', lambda x: self.overtime = int(x))
        set_yes_value('air_control', lambda x: self.gravity = Decimal(x))
        set_yes_value('telemissiles', lambda x: self.telemissiles = True)
        set_yes_value('specs_dont_disturb_players',
                      lambda x: self.specs_dont_disturb_players = True)
        set_yes_value('min_players', lambda x: self.min_players = int(x))
        set_yes_value('dmflags', lambda x: self.dmflags = True)
        set_yes_value('dmflags2', lambda x: self.dmflags2 = True)
        set_yes_value('max_clients', lambda x: self.max_clients = True)
        if self.type in ('duel', '1v1'):
            self.max_players = 2
        else:
            set_value('max_players', lambda x: self.max_players = int(x))
        set_value('timelimit', lambda x: self.timelimit = int(x))
        set_value('auto_respawn', lambda x: self.auto_respawn = int(x))
        set_value('teamdamage', lambda x: self.teamdamage = Decimal(x))
        set_value('max_teams', lambda x: self.max_teams = int(x))
        set_value('max_players_per_team':
                  lambda x: self.max_players_per_team = int(x))
        if self.type in TEAM_TYPES:
            set_value('team_score_limit', lambda x: self.scorelimit = int(x))
        ###
        # Why are we doing this...?  Commenting out to see what breaks :)
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
        template = ''
        def add_line(should_add, line):
            if should_add:
                template += line + '\n'
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
        add_line(True, 'set log_disposition "0"')
        add_var_line(self.hostname, 'set hostname "%s"')
        add_var_line(self.motd, 'set motd "%s"'))
        add_var_line(self.website, 'set website "%s"'))
        add_var_line(self.email, 'set email "%s"'))
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
        add_bool_line(self.telemissiles, 'set sv_telemissiles "%s"')
        add_bool_line(self.specs_dont_disturb_players,
                      'set specs_dont_disturb_players "%s"')
        add_bool_line(self.restart_empty_map, 'set restartemptymap "%s"')
        if self.maps:
            for map in self.maps:
                add_var_line(True, 'addmap "%s"' % (map))
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
        if self.type in DUEL_TYPES:
            self.max_players = 2
        add_var_line(self.max_players, 'set maxplayers "%s"')
        add_var_line(self.timelimit, 'set timelimit "%s"')
        add_var_line(self.fraglimit, 'set fraglimit "%s"')
        add_var_line(self.auto_respawn, 'set sv_autorespawn "%s"')
        add_var_line(self.teamdamage, 'set teamdamage "%s"')
        add_bool_line(self.type in DM_TYPES, 'set deathmatch "%s"')
        if add_bool_line(self.type in TEAM_TYPES, 'set teamplay "%s"'):
            add_var_line(self.scorelimit, 'set teamscorelimit "%s"')
        add_bool_line(self.type in CTF_TYPES, 'set ctf "%s"')
        return template # % self.config

    def watch_zserv(self, set_timer=True):
        """Watches the zserv process, restarting it if it crashes.

        set_timer: a Boolean that, if True, sets a timer to re-run
                   this method half a second after completion.  True
                   by default.

        """
        if not self.keep_spawning:
            return
        x = self.zserv.poll()
        if x:
            logging.debug('Poll: %s' % (x))
            for func in self.post_spawn_funcs:
                func()
            self.clean_up_after_zserv()
            self.spawn_zserv()
        if set_timer == True:
            Timer(.5, self.watch_zserv).start()

    def spawn_zserv(self):
        """Starts the zserv process.
        
        This keeps a reference to the running zserv process in
        self.zserv.
        
        """
        logging.info('Acquiring spawn lock [%s]' % (self.name))
        self.zdstack.spawn_lock.acquire()
        with self.zdstack.spawn_lock:
            curdir = os.getcwd()
            os.chdir(self.homedir)
            for func in self.pre_spawn_funcs:
                func()
            logging.info("Spawning [%s]" % (' '.join(self.cmd)))
            ###
            # Should we do anything with STDERR here?
            #
            # Also switched close_fds to False... I think it's required to get
            # stdout => self.logfile to work.
            ###
            self.zserv = Popen(self.cmd, stdin=PIPE, stdout=self.logfile,
                               bufsize=0, close_fds=False)
            self.send_to_zserv('players') # keeps the process from CPU spinning
            self.pid = self.zserv.pid
            os.chdir(curdir)

    def clean_up_after_zserv(self):
        """Cleans up after the zserv process exits."""
        logging.debug('')
        self.pid = None

    def start(self):
        """Starts the zserv process, restarting it if it crashes."""
        logging.debug('')
        self.pid = None
        self.logfile.start_listeners()
        self.keep_spawning = True
        self.spawn_zserv()
        if not self.already_watching:
            self.already_watching = True
            self.watch_zserv()

    def stop(self, signum=15):
        """Stops the zserv process.

        signum: an int representing the signal number to send to the
                zserv process.  15 (TERM) by default.

        """
        logging.debug('')
        self.keep_spawning = False
        self.logfile.stop_listeners()
        out = True
        if self.pid is not None:
            out = True
            try:
                os.kill(self.pid, signum)
                self.pid = None
            except Exception, e:
                es = "Caught exception while stopping: [%s]"
                logging.info(es % (e))
                out = es % (e)
        return out

    def restart(self, signum=15):
        """Restarts the zserv process, restarting it if it crashes.

        signum: an int representing the signal number to send to the
                zserv process.  15 (TERM) by default.

        """
        logging.debug('')
        self.stop(signum)
        self.start()

    def _add_player(self, player, acquire_lock=True):
        """Adds a player to self.players - threadsafe.

        player:       a Player instance
        acquire_lock: if True, will acquire self._players_lock before
                      taking any action; True by default

        """
        def blah():
            full_list = []
            name_list = []
            p_full = (player.name, player.ip, player.port)
            p_name = (player.name, player.ip)
            for p in self.players:
                full_list.append((p.name, p.ip, p.port))
                name_list.append((p.name, p.ip))
            if p_name in name_list:
                ###
                # Player reconnected
                #
                # Recreate self.disconnected_players without this player
                # Find this player in self.players and:
                #   set .port to new port
                #   set .disconnected to False
                ###
                logging.debug("Player [%s] has reconnected" % (p_name[0]))
                dp = Listable([x for x in self.disconnected_players \
                                            if (x.name, x.ip) != p_name])
                self.disconnected_players = dp
                for p in self.players:
                    if (p.name, p.ip) == p_name:
                        p.port = player.port
                        p.disconnected = False
            else:
                ###
                # Totally new connection
                ###
                logging.debug("Found totally new player [%s]" % (p_name[0]))
                self.players.append(player)
        if acquire_lock:
            with self._players_lock:
                blah()
        else:
            blah()

    def _remove_player(self, player, acquire_lock=True):
        """Disconnects a player - threadsafe.

        player:       a Player instance
        acquire_lock: if True, will acquire self._players_lock before
                      taking any action; True by default

        """
        def blah():
            player.playing = False
            player.disconnected = True
            if player in self.players and \
               player not in self.disconnected_players:
                self.disconnected_players.append(player)
        if acquire_lock:
            with self._players_lock:
                blah()
        else:
            blah()

    def sync_players(self, sleep=None):
        """Ensures that self.players matches up with self.zplayers().
        
        sleep: a float representing how much time to sleep between
               acquiring the _players_lock and creating the list of
               players; default to not sleeping at all (None)
               
        """
        zplayers = self.zplayers()
        with self._players_lock:
            if sleep:
                time.sleep(sleep)
            players_list = []
            disconnected_players_list = []
            zplayers_list = []
            zplayers_list_plus_numbers = []
            for p in self.players:
                if not p.name:
                    ###
                    # Skip players w/ blank names
                    ###
                    continue
                players_list.append((p.name, p.ip, p.port))
            for dp in self.disconnected_players:
                if not dp.name:
                    ###
                    # Skip players w/ blank names
                    ###
                    continue
                disconnected_players_list.append((dp.name, dp.ip, dp.port))
            for d in zplayers:
                if not d['player_name']:
                    ###
                    # Skip players w/ blank names
                    ###
                    continue
                zplayers_list.append((d['player_name'], d['player_ip'],
                                      d['player_port']))
                zplayers_list_plus_numbers.append((d['player_num'],
                                                   d['player_name'],
                                                   d['player_ip'],
                                                   d['player_port']))
            for z_full in zplayers_list:
                if z_full not in players_list or \
                   z_full in disconnected_players_list:
                    ###
                    # found a missing or reconnected player
                    ###
                    player = self.player_class(self, z_full[1], z_full[2],
                                               z_full[0])
                    self._add_player(player, acquire_lock=False)
                    logging.debug("Added new player [%s]" % (player.name))
            for p_full in players_list:
                if p_full not in zplayers_list: # found a ghost player
                    player = self.get_player(name=p_full[0],
                                             ip_address_and_port=p_full[1:])
                    logging.debug("Removed player [%s]" % (p_full[0]))
                    self._remove_player(player, acquire_lock=False)
            for z_full_num in zplayers_list_plus_numbers:
                for p in self.players:
                    if (p.name, p.ip, p.port) == z_full_num[1:]:
                        if p.number != z_full_num[0]:
                            if p.name.endswith('s'):
                                es = "Set %s' number to %s"
                            else:
                                es = "Set %s's number to %s"
                            logging.debug(es % (p.name, z_full_num[0]))
                            p.number = z_full_num[0]

    def add_player(self, ip_address, port):
        """Adds a player to self.players

        ip_address: a string representing a player's IP address
        port: a string representing a player's port

        """
        s = "Adding player: [%s:%s]" % (ip_address, port)
        logging.debug(s)
        self.update_player_numbers_and_ips()
        time.sleep(.2)
        ###
        # Players are uniquely identified by the combination of the IP address
        # and port number, but identity is about as far as that uniqueness
        # goes.  If players have the same name, there's no reliable way to tell
        # who fragged whom and with what.
        player = self.player_class(self, ip_address, port)
        self._add_player(player)
        self.update_player_numbers_and_ips()

    def remove_player(self, player_name):
        """Disconnects a player.

        player_name: the name of the player to disconnect
        
        """
        # logging.debug('')
        player = self.get_player(name=player_name)
        self._remove_player(player)
        self.update_player_numbers_and_ips()

    def get_player(self, name=None, ip_address_and_port=None):
        """Returns a Player instance.

        name: the name of the player to return
        ip_address_and_port: A 2-Tuple (ip_address, port), both strings

        Either name or ip_address_and_port is optional, but at least
        one must be given.  Note that only giving name can potentially
        return the wrong player, as multiple players can have the same
        name.

        """
        # logging.debug('')
        if name and ip_address_and_port:
            ip_address, port = ip_address_and_port
            cf = lambda x: x.name == name and \
                           x.ip == ip_address and \
                           x.port == port
        elif name:
            cf = lambda x: x.name == name
        elif ip_address_and_port:
            ip_address, port = ip_address_and_port
            cf = lambda x: x.ip == ip_address and x.port == port
        else:
            raise ValueError("One of name or ip_address_and_port is required")
        for player in self.players:
            if cf(player):
                return player
        self.sync_players()
        for player in self.players:
            if cf(player):
                return player
        raise PlayerNotFoundError(name, ip_address_and_port)

    def update_player_numbers_and_ips(self):
        """Sets player numbers and IP addresses.

        This method needs to be run upon every connection and
        disconnection if numbers and names are to remain in sync.

        """
        for d in self.zplayers():
            try:
                p = self.get_player(ip_address_and_port=(d['player_ip'],
                                                         d['player_port']))
            except PlayerNotFoundError, pnfe:
                es = "Players out of sync, %s at %s:%s not found"
                logging.debug(es % (d['player_name'], d['player_ip'],
                                    d['player_port']))
                continue
            except ValueError, e:
                logging.debug("ValueError in upnai: %s" % (e))
                continue
            except Exception, e:
                logging.debug("Error updating player #s and IPs: %s" % (e))
                continue
            p.set_name(d['player_name'])
            p.number = d['player_num']
            es = "Set name/number %s/%s to address %s:%s"
            logging.debug(es % (p.name, p.number, p.ip, p.port))

    def distill_player(self, possible_player_names):
        """Discerns the most likely existing player.

        possible_player_names: a list of strings representing possible
                               player names

        Because messages are formatted in such a way that separating
        messenger's name from the message is not straightforward, this
        method will return the most likely player name from a list of
        possible messenger names.  This method has other uses, but
        that's the primary one.

        """
        messenger = None
        names = [x.name for x in self.players]
        def blah():
            for player_name in possible_player_names:
                if player_name in names:
                    return self.get_player(name=player_name)
        messenger = blah()
        if not messenger:
            self.sync_players()
            names = [x.name for x in self.players]
            messenger = blah()
        # if not messenger:
        #     player_names = ', '.join(names)
        #     ppn = ', '.join(possible_player_names)
        #     logging.info("No player could be distilled")
        #     logging.info("Players: [%s]" % (player_names))
        #     logging.info("Possible: [%s]" % (ppn))
        return messenger

    def get_player_ip_address(self, player_name):
        """Returns a player's IP address.
        
        player_name: a string representing the name of the player
                     whose IP address is to be returned

        """
        d = [x for x in self.zplayers() if x['player_name'] == player_name]
        if not d:
            raise ValueError("Player [%s] not found" % (player_name))
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
            raise ValueError("Player [%s] not found" % (player_name))
        return d[0]['player_num']

    def handle_message(self, message, messenger):
        """Handles a message.

        message:   a string representing the message
        messenger: a string representing the name of the messenger

        """
        ###
        # This is handled by plugins now, someday I'll fully remove the
        # references to this.
        ###
        pass

    def change_map(self, map_number, map_name):
        """Handles a map change event.

        map_number: an int representing the number of the new map
        map_name:   a string representing the name of the new map

        """
        # logging.debug('')
        self.map = self.map_class(map_number, map_name)
        self.players = [x for x in self.players \
                            if x not in self.disconnected_players]
        self.players = Listable(self.players)
        for player in self.players:
            player.initialize()
            player.set_map(self.map)
        self.disconnected_players = Listable()

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
        with self._zserv_stdin_lock:
            ###
            # zserv's STDIN is (obviously) not threadsafe, so we need to ensure
            # that access to it is limited to 1 thread at a time, which is both
            # writing to it, and waiting for responses from its STDOUT.
            ###
            if event_response_type is not None:
                self.general_log.watch_for_response(event_response_type)
            self.zserv.stdin.write(message + '\n')
            self.zserv.stdin.flush()
            if event_response_type is not None:
                return self.general_log.get_response()

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
             'type': self.type,
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

