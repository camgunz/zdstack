import os
from decimal import Decimal
from datetime import date, datetime, timedelta
from threading import Event
from subprocess import Popen, PIPE

from pyfileutils import write_file

from ZDStack import yes, no, ZSERV_EXE, HOSTNAME
from ZDStack.Map import Map
from ZDStack.Team import Team
from ZDStack.Alarm import Alarm
from ZDStack.LogFile import LogFile
from ZDStack.Dictable import Dictable
from ZDStack.Listable import Listable
from ZDStack.LogParser import ConnectionLogParser, WeaponLogParser, \
                              GeneralLogParser
from ZDStack.LogListener import ConnectionLogListener, WeaponLogListener, \
                                GeneralLogListener

class ZServ:

    def __init__(self, name, type, config, zdstack):
        """Initializes a ZServ instance.

        name:    a string representing the name of this ZServ.
        config:  a dict of configuration values for this ZServ.
        zdstack: the calling ZDStack instance

        """
        ###
        # TODO:
        #   1. It would be good if somehow maps where no one joins a team are
        #   not counted towards the number of maps to remember (why replace
        #   maps where stats actually exist with ones where they don't?).
        ###
        self.start_time = datetime.now()
        self.name = name
        self.type = type
        self.zdstack = zdstack
        self.dn_fobj = open('/dev/null', 'r+')
        self.devnull = self.dn_fobj.fileno()
        self.homedir = os.path.join(self.zdstack.homedir, self.name)
        self.pid_file = os.path.join(self.homedir, self.name + '.pid')
        if not os.path.isdir(self.homedir):
            os.mkdir(self.homedir)
        self.configfile = os.path.join(self.homedir, self.name + '.cfg')
        self.keep_spawning = Event()
        self.log = lambda x: self.zdstack.log('%s: %s' % (self.name, x))
        def is_valid(x):
            return x in config and config[x]
        def is_yes(x):
            return x in config and yes(config[x])
        self.remembered_maps = []
        ### mandatory stuff
        mandatory_options = ('iwad', 'waddir', 'iwaddir', 'wads', 'port',
                             'maps_to_remember')
        for mandatory_option in mandatory_options:
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
        self.cmd = [config['zserv_exe'], '-waddir', self.waddir, '-iwad', self.iwad,
                    '-port', str(self.port), '-cfg', self.configfile, '-clog',
                    '-wlog', '-log']
        for wad in self.wads:
            self.cmd.extend(['-file', wad])
        # self.cmd.extend(['-noinput'])
        ### other mandatory stuff
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
            self.deathlimit = int(config['deathlimit'])
        if is_valid('spam_window'):
            self.spam_window = int(config['spam_window'])
        if is_valid('spam_limit'):
            self.spam_limit = int(config['spam_limit'])
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
            self.skill = int(config['skill'])
        if is_valid('gravity'):
            self.gravity = int(config['gravity'])
        if is_valid('air_control'):
            self.air_control = Decimal(config['air_control'])
        if is_valid('min_players'):
            self.min_players = int(config['min_players'])
        config['name'] = self.name
        self.config = config
        self.configuration = self.get_configuration()
        write_file(self.configuration, self.configfile, overwrite=True)
        self.set_log_switch_alarm()
        self.initialize()

    def set_log_switch_alarm(self):
        now = datetime.now()
        today = datetime(now.year, now.month, now.day)
        tomorrow = today + timedelta(days=1)
        Alarm(tomorrow, self.switch_logs).start()

    def switch_logs(self):
        if self.connection_log:
            self.connection_log.set_filepath(self.get_connection_log_filename())
        if self.weapon_log:
            self.weapon_log.set_filepath(self.get_weapon_log_filename())
        if self.general_log:
            self.general_log.set_filepath(self.get_general_log_filename())
        self.set_log_switch_alarm()

    def initialize(self):
        self.map = None
        self.red_team = Team('red')
        self.blue_team = Team('blue')
        self.green_team = Team('green')
        self.white_team = Team('white')
        self.teams = Dictable({'red': self.red_team,
                               'blue': self.blue_team,
                               'green': self.green_team,
                               'white': self.white_team})
        self.players = Dictable()
        self.pid = None
        self.connection_log = None
        self.general_log = None
        self.weapon_log = None
        if os.path.isfile(self.pid_file):
            os.unlink(self.pid_file)

    def get_configuration(self):
        # TODO: add support for "add_mapnum_to_hostname"
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
        else:
            template += 'set master_advertise "0"\n'
        if self.rcon_enabled:
            template += 'set enable_rcon "1"\n'
            template += 'set rcon_password "%s"\n' % (self.rcon_password)
        else:
            template += 'set enable_rcon "0"\n'
        if self.requires_password:
            template += 'set force_password "1"\n'
            template += 'set password "%s"\n' % (self.server_password)
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
            optional_wads = ' '.join(self.optional_wads)
            template += optional_wads.join(['set optional_wads "', '"\n'])
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
            template += 'set maxclients "%s"\n' % (self.max_clients)
        if self.max_players:
            template += 'set maxplayers "%s"\n' % (self.max_players)
        if self.max_teams:
            template += 'set maxteams "%s"\n' % (self.max_teams)
        if self.max_players_per_team:
            template += 'set maxplayersperteam "%s"\n' % \
                                                    (self.max_players_per_team)
        if self.timelimit:
            template += 'set timelimit "%s"\n' % (self.timelimit)
        if self.fraglimit:
            template += 'set fraglimit "%s"\n' % (self.fraglimit)
        if self.scorelimit:
            template += 'set teamscorelimit "%s"\n' % (self.scorelimit)
        return template % self.config

    def start(self):
        self.keep_spawning.set()
        while 1:
            self.keep_spawning.wait()
            self.initialize()
            connection_log_filename = self.get_connection_log_filename()
            weapon_log_filename = self.get_weapon_log_filename()
            general_log_filename = self.get_general_log_filename()
            connection_log_parser = ConnectionLogParser()
            weapon_log_parser = WeaponLogParser()
            general_log_parser = GeneralLogParser()
            self.connection_log_listener = ConnectionLogListener(self)
            self.weapon_log_listener = WeaponLogListener(self)
            self.general_log_listener = GeneralLogListener(self)
            self.connection_log = LogFile(connection_log_filename,
                                          'connection',
                                          connection_log_parser, self)
            self.weapon_log = \
                    LogFile(weapon_log_filename, 'weapon', weapon_log_parser, self)
            self.general_log = \
                    LogFile(general_log_filename, 'general', general_log_parser, self)
            self.connection_log.listeners.append(self.connection_log_listener)
            self.weapon_log.listeners.append(self.weapon_log_listener)
            self.general_log.listeners.append(self.general_log_listener)
            self.log("Spawning [%s]" % (' '.join(self.cmd)))
            curdir = os.getcwd()
            os.chdir(self.homedir)
            # while 1:
            #     time.sleep(1)
            self.zserv = Popen(self.cmd, stdin=PIPE, stdout=self.devnull,
                               bufsize=0, close_fds=True)
            self.pid = self.zserv.pid
            write_file(str(self.pid), self.pid_file)
            os.chdir(curdir)
            self.zserv.wait()
            # The zserv process has exited and we restart all over again

    def stop(self, signum=15):
        self.keep_spawning.clear()
        try:
            s = "Sending signal %s to %s PID: %s"
            self.log(s % (signum, self.name, self.pid))
            os.kill(self.pid, signum)
            return True
        except Exception, e:
            es = str(e)
            self.log(es)
            return es

    def restart(self, signum=15):
        self.stop(signum)
        self.start()

    def send_to_zserv(self, message):
        self.zserv.stdin.write(message)
        self.zserv.stdin.flush()

    def get_logfile_suffix(self):
        return date.today().strftime('-%Y%m%d') + '.log'

    def get_connection_log_filename(self):
        return os.path.join(self.homedir, 'conn' + self.get_logfile_suffix())

    def get_weapon_log_filename(self):
        return os.path.join(self.homedir, 'weap' + self.get_logfile_suffix())

    def get_general_log_filename(self):
        return os.path.join(self.homedir, 'gen' + self.get_logfile_suffix())

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

    def get_player(self, name):
        if name not in self.players:
            # Maybe we should make custom exceptions like PlayerNotFoundError
            raise ValueError("Player [%s] not found" % (name))
        return self.players[name]

    def get_team(self, color):
        if color not in self.teams:
            # Maybe we should make custom exceptions like TeamNotFoundError
            raise ValueError("%s team not found" % (color.capitalize()))
        return self.teams[color]

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
        messager = None
        for player_name in possible_player_names:
            if player_name in self.players:
                messager = self.players[player_name]
                break
        if messager is None:
            es = "Received a message but none of the players existed: [%s]"
            self.log(es % (', '.join(possible_player_names)))
        else:
            message = message.replace(messager.name, '', 1)[3:]
            es = "Received a message [%s] from player [%s]"
            self.log(es % (message, messager.name))
            ###
            # Here we would do the lookup
            ###
            pass

    def handle_map_change(self, map_number, map_name):
        ###
        # TODO:
        #   Don't remember maps where no one joined a game/team.
        ###
        if len(self.remembered_maps) == self.maps_to_remember:
            self.remembered_maps = self.remembered_maps[1:]
        self.remembered_maps.append(self.map)
        self.map = Map(map_number, map_name)
        self.red_team = Team('red')
        self.blue_team = Team('blue')
        self.green_team = Team('green')
        self.white_team = Team('white')
        self.teams = Dictable({'red': self.red_team,
                               'blue': self.blue_team,
                               'green': self.green_team,
                               'white': self.white_team})
        self.players = Dictable()
        for color, team in self.teams.items():
            if type(team) != type([]):
                team.set_map(self.map)
            else:
                print "Skipping team [%s], because it's a list" % (color)

