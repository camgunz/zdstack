import os
from decimal import Decimal
from datetime import datetime, timedelta

from ZDStack import yes, no
from ZDStack.Map import Map
from ZDStack.Team import Team
from ZDStack.LogFile import LogFile
from ZDStack.Listable import Listable
from ZDStack.LogParser import ConnectionLogParser, WeaponLogParser, \
                              GeneralLogParser
from ZDStack.LogListener import ConnectionLogListener, WeaponLogListener, \
                                GeneralLogListener

class ZServ:

    def __init__(self, name, config, zdstack):
        """Initializes a ZServ instance.

        name:    a string representing the name of this ZServ.
        config:  a dict of configuration values for this ZServ.
        zdstack: the calling ZDStack instance

        """
        ###
        # TODO:
        #   1. game-mode-specific stuff is not normalized in the config, for
        #   instance, if no dmflags are specified for a CTF server, the
        #   configuration value for 'ctf_dmflags' is used... if it's valid.
        #   However, the value inside 'config' for 'dmflags' is not changed
        #   to the valiue inside 'config' for 'ctf_dmflags', so if, say,
        #   config['hostname'] == 'Great Servers, good dmflags (%(dmflags)s)',
        #   The hostname will be broken.  Really, to fix this, we have to
        #   change...
        #
        #   2. Dear Lord is this crap long.  Especially the game-mode-specific
        #   stuff, that really needs to be looped up somehow.  Maybe what I'll
        #   do is subclass into something like TeamDM, Duel, FFA, CTF and Coop,
        #   so every game-mode has its own class and we can avoid configuration
        #   for other game-modes.  That saves about 1/2 this function, while
        #   adding logic to ZDStack.  Even though it kinda seems like needless
        #   classing, I feel like that's the best solution.
        #
        #   3. These values should be properly typed, like, fraglimit ought to
        #   be an int.  Look for this to be changed when this is split up into
        #   game-mode classes.
        #
        #   4. It would be good if somehow maps where no one joins a team are
        #   not counted towards the number of maps to remember (why replace
        #   maps where stats actually exist with ones where they don't?).
        ###
        self.start_time = datetime.now()
        self.name = name
        self.zdstack = zdstack
        self.keep_spawning = Event()
        self.zserv_pid = None
        self.connection_log = None
        self.general_log = None
        self.weapon_log = None
        self.log = lambda x: self.zdstack.log('%s: %s' % (self.name, x))
        def is_valid(x):
            return x in config and config[x]
        def is_yes(x):
            return x in config and yes(x)
        ### mandatory stuff
        mandatory_options = ('base_iwad', 'iwad', 'waddir', 'iwaddir', 'wads',
                             'port', 'type', 'maps_to_remember')
        for mandatory_option in mandatory_option:
            if mandatory_option not in config:
                es = "Could not find option '%s' in configuration"
                raise ValueError(es % (mandatory_option))
        ### CMD-line stuff
        self.iwaddir = config['iwaddir']
        self.waddir = config['waddir']
        self.base_iwad = config['iwad']
        self.iwad = os.path.join(self.iwaddir, self.base_iwad)
        self.wads = config['wads'].split(',')
        self.wads = [os.path.join(self.waddir, x) for x in self.wads if x]
        self.port = int(config['port'])
        self.maps_to_remember = int(config['maps_to_remember'])
        if not os.path.isdir(self.iwaddir):
            raise ValueError("IWAD dir %s is not valid" % (self.waddir))
        if not os.path.isdir(self.waddir):
            raise ValueError("WAD dir %s is not valid" % (self.waddir))
        if not os.path.isfile(self.iwad):
            raise ValueError("Could not find IWAD %s" % (self.iwad))
        for wad in self.wads:
            if not os.path.isfile(wad):
                raise ValueError("WAD %s not found" % (wad))
        self.cmd = [ZSERV_EXE, '-noinput', '-waddir', self.waddir, '-iwad',
                    self.iwad, '-port', str(self.port), '-cfg',
                    configfile, '-clog', '-wlog']
        for wad in self.wads:
            self.cmd.extend(['-file', wad])
        ### other mandatory stuff
        self.type = config['type'].lower()
        self.address = 'http://%s:%d' % (HOSTNAME, self.port)
        ### admin stuff
        self.rcon_enabled = None
        self.requires_password = None
        self.rcon_password = None
        self.server_password = None
        self.deathlimit = None
        self.spam_window = None
        self.spam_limit = None
        self.speed_check = None
        self.restart_empty_map = None
        ### advertise stuff
        self.admin_email = None
        self.advertise = None
        self.hostname = None
        self.website = None
        self.motd = None
        self.add_mapnum_to_hostname = None
        ### config stuff
            ### game-mode-agnostic stuff
        self.remove_bots_when_humans = None
        self.maps = None
        self.optional_wads = None
        self.overtime = None
        self.skill = None
        self.gravity = None
        self.air_control = None
        self.min_players = None
            ### game-mode-specific stuff
        self.dmflags = None
        self.dmflags2 = None
        self.teamdamage = None
        self.max_clients = None
        self.max_players = None
        self.max_teams = None
        self.max_players_per_team = None
        self.timelimit = None
        self.fraglimit = None
        self.scorelimit = None
        ### Load admin stuff
        if is_yes('rcon_enabled'):
            self.rcon_enabled = True
        if is_yes('requires_password'):
            self.requires_password = True
        if self.rcon_enabled and is_valid('rcon_password'):
            self.rcon_password = config['rcon_password']
        if self.requires_password and is_valid('server_password'):
            self.server_password = config['server_password']
        if is_valid('deathlimit'):
            self.deathlimit = config['deathlimit']
        if is_valid('spam_window'):
            self.spam_window = config['spam_window']
        if is_valid('spam_limit'):
            self.spam_limit = config['spam_limit']
        if is_yes('speed_check'):
            self.speed_check = True
        if is_yes('restart_empty_map'):
            self.restart_empty_map = True
        ### Load advertise stuff
        if is_valid('admin_email'):
            self.admin_email = config['admin_email']
        if is_yes('advertise'):
            self.advertise = True
        if is_valid('hostname'):
            self.hostname = config['hostname']
        if is_valid('website'):
            self.website = config['website']
        if is_valid('motd'):
            self.motd = config['motd']
        if is_yes('add_mapnum_to_hostname'):
            self.add_mapnum_to_hostname = True
        ### Load game-mode-agnostic config stuff
        if is_yes('remove_bots_when_humans'):
            self.remove_bots_when_humans = True
        if is_valid('maps'):
            self.maps = [x for x in config['maps'].split(',') if x]
        if is_valid('optional_wads'):
            self.optional_wads = \
                    [x for x in config['optional_wads'].split(',') if x]
        if is_yes('overtime'):
            self.overtime = True
        if is_valid('skill'):
            self.skill = config['skill']
        if is_valid('gravity'):
            self.gravity = config['gravity']
        if is_valid('air_control'):
            self.air_control = config['air_control']
        if is_valid('min_players'):
            self.min_players = config['min_players']
        ### Load default game-mode-specific config stuff
        if self.type in ('ctf', 'teamdm'):
            self.deathmatch = True
            self.teamplay = True
            if self.type == 'ctf':
                self.ctf = True
                if is_valid('dmflags'):
                    self.dmflags = config['dmflags']
                elif is_valid('ctf_dmflags'):
                    self.dmflags = config['ctf_dmflags']
                if is_valid('dmflags2'):
                    self.dmflags2 = config['dmflags2']
                elif is_valid('ctf_dmflags2'):
                    self.dmflags2 = config['ctf_dmflags2']
                if is_valid('teamdamage'):
                    self.teamdamage = config['teamdamage']
                elif is_valid('ctf_teamdamage'):
                    self.teamdamage = config['ctf_teamdamage']
                if is_valid('max_clients'):
                    self.max_clients = config['max_clients']
                elif is_valid('ctf_max_clients'):
                    self.max_clients = config['ctf_max_clients']
                if is_valid('max_players'):
                    self.max_players = config['max_players']
                elif is_valid('ctf_max_players'):
                    self.max_players = config['ctf_max_players']
                if is_valid('max_teams'):
                    self.max_teams = config['max_teams']
                elif is_valid('ctf_max_teams'):
                    self.max_teams = config['ctf_max_teams']
                if is_valid('max_players_per_team'):
                    self.max_players_per_team = \
                                            config['max_players_per_team']
                elif is_valid('ctf_max_players_per_team'):
                    self.max_players_per_team = \
                                        config['ctf_max_players_per_team']
                if is_valid('timelimit'):
                    self.timelimit = config['timelimit']
                elif is_valid('ctf_timelimit'):
                    self.timelimit = config['ctf_timelimit']
                if is_valid('scorelimit'):
                    self.scorelimit = config['scorelimit']
                elif is_valid('ctf_scorelimit'):
                    self.scorelimit = config['ctf_scorelimit']
            elif self.type == 'teamdm':
                self.ctf = False
                if is_valid('dmflags'):
                    self.dmflags = config['dmflags']
                elif is_valid('teamdm_dmflags'):
                    self.dmflags = config['teamdm_dmflags']
                if is_valid('dmflags2'):
                    self.dmflags2 = config['dmflags2']
                elif is_valid('teamdm_dmflags2'):
                    self.dmflags2 = config['teamdm_dmflags2']
                if is_valid('teamdamage'):
                    self.teamdamage = config['teamdamage']
                elif is_valid('teamdm_teamdamage'):
                    self.teamdamage = config['teamdm_teamdamage']
                if is_valid('max_clients'):
                    self.max_clients = config['max_clients']
                elif is_valid('teamdm_max_clients'):
                    self.max_clients = config['teamdm_max_clients']
                if is_valid('max_players'):
                    self.max_players = config['max_players']
                elif is_valid('teamdm_max_players'):
                    self.max_players = config['teamdm_max_players']
                if is_valid('max_teams'):
                    self.max_teams = config['max_teams']
                elif is_valid('teamdm_max_teams'):
                    self.max_teams = config['teamdm_max_teams']
                if is_valid('max_players_per_team'):
                    self.max_players_per_team = \
                                        config['max_players_per_team']
                elif is_valid('teamdm_max_players_per_team'):
                    self.max_players_per_team = \
                                    config['teamdm_max_players_per_team']
                if is_valid('timelimit'):
                    self.timelimit = config['timelimit']
                elif is_valid('teamdm_timelimit'):
                    self.timelimit = config['teamdm_timelimit']
                if is_valid('scorelimit'):
                    self.scorelimit = config['scorelimit']
                elif is_valid('teamdm_scorelimit'):
                    self.scorelimit = config['teamdm_scorelimit']
        elif self.type in ('1-on-1', 'duel', 'ffa', 'coop'):
            self.teamplay = False
            self.ctf = False
            if self.type in ('1-on-1', 'duel', 'ffa'):
                self.deathmatch = True
            else:
                self.deathmatch = False
            if self.type in ('1-on-1', 'duel'):
                if is_valid('dmflags'):
                    self.dmflags = config['dmflags']
                elif is_valid('duel_dmflags'):
                    self.dmflags = config['duel_dmflags']
                if is_valid('dmflags2'):
                    self.dmflags2 = config['dmflags2']
                elif is_valid('duel_dmflags2'):
                    self.dmflags2 = config['duel_dmflags2']
                if is_valid('max_clients'):
                    self.max_clients = config['max_clients']
                elif is_valid('duel_max_clients'):
                    self.max_clients = config['duel_max_clients']
                if is_valid('max_players'):
                    self.max_players = config['max_players']
                elif is_valid('duel_max_players'):
                    self.max_players = config['duel_max_players']
                if is_valid('timelimit'):
                    self.timelimit = config['timelimit']
                elif is_valid('duel_timelimit'):
                    self.timelimit = config['duel_timelimit']
                if is_valid('fraglimit'):
                    self.fraglimit = config['fraglimit']
                elif is_valid('duel_fraglimit'):
                    self.fraglimit = config['duel_fraglimit']
            elif self.type == 'ffa':
                if is_valid('dmflags'):
                    self.dmflags = config['dmflags']
                elif is_valid('ffa_dmflags'):
                    self.dmflags = config['ffa_dmflags']
                if is_valid('dmflags2'):
                    self.dmflags2 = config['dmflags2']
                elif is_valid('ffa_dmflags2'):
                    self.dmflags2 = config['ffa_dmflags2']
                if is_valid('max_clients'):
                    self.max_clients = config['max_clients']
                elif is_valid('ffa_max_clients'):
                    self.max_clients = config['ffa_max_clients']
                if is_valid('max_players'):
                    self.max_players = config['max_players']
                elif is_valid('ffa_max_players'):
                    self.max_players = config['ffa_max_players']
                if is_valid('timelimit'):
                    self.timelimit = config['timelimit']
                elif is_valid('ffa_timelimit'):
                    self.timelimit = config['ffa_timelimit']
                if is_valid('fraglimit'):
                    self.fraglimit = config['fraglimit']
                elif is_valid('ffa_fraglimit'):
                    self.fraglimit = config['ffa_fraglimit']
            elif self.type == 'coop':
                if is_valid('dmflags'):
                    self.dmflags = config['dmflags']
                elif is_valid('coop_dmflags'):
                    self.dmflags = config['coop_dmflags']
                if is_valid('dmflags2'):
                    self.dmflags2 = config['dmflags2']
                elif is_valid('coop_dmflags2'):
                    self.dmflags2 = config['coop_dmflags2']
                if is_valid('teamdamage'):
                    self.teamdamage = config['teamdamage']
                elif is_valid('coop_teamdamage'):
                    self.teamdamage = config['coop_teamdamage']
                if is_valid('max_clients'):
                    self.max_clients = config['max_clients']
                elif is_valid('coop_max_clients'):
                    self.max_clients = config['coop_max_clients']
                if is_valid('max_players'):
                    self.max_players = config['max_players']
                elif is_valid('coop_max_players'):
                    self.max_players = config['coop_max_players']
                if is_valid('timelimit'):
                    self.timelimit = config['timelimit']
                elif is_valid('coop_timelimit'):
                    self.timelimit = config['coop_timelimit']
            else:
                raise ValueError("Unsupported game type [%s]" % (self.type))
        template = 'set cfg_activated "1"\n'
        if self.hostname:
            template += 'set hostname "%s"\n' % (self.hostname)
        if self.motd:
            template += 'set motd "%s"\n' % (self.motd)
        if self.website:
            template += 'set website "%s"\n' % (self.website)
        if self.admin_email:
            template += 'set email "%s"\n' % (self.admin_email)
        if self.advertise:
            template += 'set master_advertise "1"\n'
        if self.rcon_enabled:
            template += 'set enable_rcon "1"\n'
            template += 'set rcon_password "%s"\n' % (self.rcon_password)
        else:
            template += 'set enable_rcon "0"\n'
        if self.requires_password:
            template += 'set force_password "1"\n'
            template += 'set server_password "%s"\n' % (self.server_password)
        else:
            template += 'set force_password "0"\n'
        if self.deathlimit:
            template += 'set deathlimit "%s"\n' % (self.deathlimit)
        if self.spam_window:
            template += 'set spam_window "%s"\n' % (self.spam_window)
        if self.spam_limit:
            template += 'set spam_limit "%s"\n' % (self.spam_limit)
        if self.speed_check:
            template += 'set speed_check "1"\n'
        else:
            template += 'set speed_check "0"\n'
        if self.restart_empty_map:
            template += 'set restartemptymap "1"\n'
        if self.maps:
            for map in self.maps:
                template += 'addmap "%s"\n' % (map)
        if self.optional_wads:
            template += ' '.join(self.optional_wads) + '\n'
        if self.overtime:
            for map in self.maps:
                template += 'add_cvaroverride %s overtime 1\n' % (map)
        else:
            for map in self.maps:
                template += 'add_cvaroverride %s overtime 0\n' % (map)
        if self.skill:
            template += 'set skill "%s"\n' % (self.skill)
        if self.gravity:
            template += 'set gravity "%s"\n' % (self.gravity)
        if self.air_control:
            template += 'set sv_aircontrol "%s"\n' % (self.air_control)
        if self.min_players:
            template += 'set minplayers "%s"\n' % (self.min_players)
        if self.remove_bots_when_humans:
            template += 'set removebotswhenhumans "1"\n'
        else:
            template += 'set removebotswhenhumans "0"\n'
        if self.dmflags:
            template += 'set dmflags "%s"\n' % (self.dmflags)
        if self.dmflags2:
            template += 'set dmflags2 "%s"\n' % (self.dmflags2)
        if self.teamdamage:
            template += 'set teamdamage "%s"\n' % (self.teamdamage)
        if self.max_clients:
            template += 'set max_clients "%s"\n' % (self.max_clients)
        if self.max_players:
            template += 'set max_players "%s"\n' % (self.max_players)
        if self.max_teams:
            template += 'set max_teams "%s"\n' % (self.max_teams)
        if self.max_players_per_team:
            template += 'set max_players_per_team "%s"\n' % \
                                                    (self.max_players_per_team)
        if self.timelimit:
            template += 'set timelimit "%s"\n' % (self.timelimit)
        if self.fraglimit:
            template += 'set fraglimit "%s"\n' % (self.fraglimit)
        if self.scorelimit:
            template += 'set team_scorelimit "%s"\n' % (self.scorelimit)
        config['name'] = self.name
        self.configuration = template % config
        self.pid = None
        self.connection_log = None
        self.general_log = None
        self.weapon_log = None
        self.red_team = Team('red')
        self.blue_team = Team('blue')
        self.green_team = Team('green')
        self.white_team = Team('white')
        self.map = None
        self.teams = {'red': self.red_team, 'blue': self.blue_team,
                      'green': self.green_team, 'white': self.white_team}
        self.players = {}

    def start(self):
        self.keep_spawning.set()
        while 1:
            self.keep_spawning.wait()
            self.connection_log = LogFile(self.get_connection_log_file(),
                                          'connection', ConnectionLogParser())
            self.general_log = LogFile(self.get_general_log_file(),
                                          'general', GeneralLogParser())
            self.weapon_log = LogFile(self.get_weapon_log_file(),
                                          'weapon', WeaponLogParser())
            connection_log_listener = ConnectionLogListener(self)
            weapon_log_listener = WeaponLogListener(self)
            general_log_listener = GeneralLogListener(self)
            self.connection_log.listeners.append(connection_log_listener)
            self.weapon_log.listeners.append(weapon_log_listener)
            self.general_log.listeners.append(general_log_listener)
            self.log("Spawning [%s]" % (' '.join(self.cmd))
            self.pid = os.spawnv(os.P_NOWAIT, self.cmd[0], self.cmd)
            os.waitpid(self.zserv_pid, 0)
            self.pid = None
            self.connection_log = None
            self.general_log = None
            self.weapon_log = None

    def stop(self, signum=15):
        self.keep_spawning.clear()
        try:
            s = "Sending signal %s to %s PID: %s"
            self.log(s % (signum, self.name, self.pid)
            os.kill(self.zserv_pid, signum)
            return True
        except Exception, e:
            es = str(e)
            self.log(es)
            return es

    def restart(self, signum=15):
        self.stop(signum)
        self.start()

    def add_player(self, player):
        ###
        # It's possible for players to have the same name, so that this
        # function will do nothing.  There's absolutely nothing we can do
        # about this, stats are just fucked for those players.  Basically, the
        # first player in line gets all the action.  In a way, it's funny
        # because a group of people could all join a server under the same
        # name, and blow up stats for a certain player.
        ###
        if player.name not in self.players:
            self.players[player.name] = player

    def remove_player(self, player):
        if player.name in self.players:
            del self.players[player.name]

    def get_player(self, player):
        if player.name not in self.players:
            # Maybe we should make custom exceptions like PlayerNotFoundError
            raise ValueError("Player [%s] not found" % (player.name))
        return self.players[player.name]

    def get_team(self, team):
        if team.color not in self.teams:
            # Maybe we should make custom exceptions like TeamNotFoundError
            raise ValueError("%s team not found" % (team.color.capitalize()))
        return self.teams[team.color]

    def handle_message(self, message, possible_player_names):
        ###
        # I think the way this will work is we will check the messager's
        # homogenized name against some list of messagers and regexp pairs.
        # Then, we can take a specific action like "kick" or "say".  So,
        # something like:
        #
        # mionicd: "^no$" kick
        #
        ###
        player_names = self.players.keys()
        messager = None
        for player_name in possible_player_names:
            if player_name in player_names:
                messager = player_names[player_name]
        if messager is None:
            es = "Received a message from a non-existant player [%s]!"
            self.log(es % (player_name))
        else:
            ###
            # Here we would do the lookup
            ###
            pass

    def handle_map_change_event(self, map_number, map_name):
        ###
        # TODO:
        #   Need to add an option "maps_to_remember".  Also, it would be good
        #   if somehow maps where no one joins a team are not counted towards
        #   the number of maps to remember (why replace maps where stats
        #   actually exist with ones where they don't?).
        ###
        new_map = Map(map_number, map_name)
        for team in self.teams.values():
            team.set_map(new_map)
        if len(self.remembered_maps) == self.maps_to_remember:
            self.remembered_maps = self.remembered_maps[1:]
        self.remembered_maps.append(new_map)

