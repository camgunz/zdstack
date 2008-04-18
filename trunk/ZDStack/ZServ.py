import os
from decimal import Decimal
from datetime import date, datetime, timedelta
from subprocess import Popen, PIPE

from pyfileutils import read_file, write_file

from ZDStack import yes, no, start_thread, HOSTNAME
from ZDStack.Stats import Stats
from ZDStack.LogFile import LogFile
from ZDStack.Dictable import Dictable
from ZDStack.Listable import Listable
from ZDStack.BaseMap import BaseMap
from ZDStack.BaseTeam import BaseTeam
from ZDStack.BasePlayer import BasePlayer
from ZDStack.LogParser import ConnectionLogParser,  GeneralLogParser
from ZDStack.LogListener import ConnectionLogListener, GeneralLogListener

class ZServ:

    def __init__(self, name, type, config, zdstack, player_class=BasePlayer,
                                                    team_class=BaseTeam,
                                                    map_class=BaseMap):
        """Initializes a ZServ instance.

        name:    a string representing the name of this ZServ.
        config:  a dict of configuration values for this ZServ.
        zdstack: the calling ZDStack instance

        """
        ###
        # TODO:
        #   1. It would be good if somehow maps where no one joins the game
        #   are not counted towards the number of maps to remember (why
        #   replace maps where stats actually exist with ones where they
        #   don't?).
        ###
        self.start_time = datetime.now()
        self.name = name
        self.type = type
        self.zdstack = zdstack
        self.map_class = map_class
        self.team_class = team_class
        self.player_class = player_class
        self.dn_fobj = open('/dev/null', 'r+')
        self.devnull = self.dn_fobj.fileno()
        self.homedir = os.path.join(self.zdstack.homedir, self.name)
        self.old_log_dir = os.path.join(self.homedir, 'old-logs')
        self.pid_file = os.path.join(self.homedir, self.name + '.pid')
        if not os.path.isdir(self.homedir):
            os.mkdir(self.homedir)
        self.configfile = os.path.join(self.homedir, self.name + '.cfg')
        self.keep_spawning = False
        self.spawning_thread = None
        self.log = lambda x: self.zdstack.log('%s: %s' % (self.name, x))
        self.remembered_stats = Listable()
        self.reload_config(config)
        self.pid = None

    def reload_config(self, config):
        self.load_config(config)
        self.configuration = self.get_configuration()
        write_file(self.configuration, self.configfile, overwrite=True)

    def load_config(self, config):
        def is_valid(x):
            return x in config and config[x]
        def is_yes(x):
            return x in config and yes(config[x])
        ### mandatory stuff
        mandatory_options = \
                    ('iwad', 'waddir', 'iwaddir', 'port', 'maps_to_remember')
        for mandatory_option in mandatory_options:
            if mandatory_option not in config:
                es = "Could not find option '%s' in configuration"
                raise ValueError(es % (mandatory_option))
        ### CMD-line stuff
        if not os.path.isdir(config['iwaddir']):
            raise ValueError("IWAD dir %s is not valid" % (config['waddir']))
        if not os.path.isdir(config['waddir']):
            raise ValueError("WAD dir %s is not valid" % (config['waddir']))
        if not os.path.isfile(os.path.join(config['iwaddir'], config['iwad'])):
            raise ValueError("Could not find IWAD %s" % (config['iwad']))
        self.wads = []
        if 'wads' in config and config['wads']:
            for wad in config['wads'].split(','):
                wadpath = os.path.join(config['waddir'], wad)
                if not os.path.isfile(wadpath):
                    raise ValueError("WAD [%s] not found" % (wad))
            self.wads = config['wads'].split(',')
        self.iwaddir = config['iwaddir']
        self.waddir = config['waddir']
        self.base_iwad = config['iwad']
        self.iwad = os.path.join(self.iwaddir, self.base_iwad)
        self.port = int(config['port'])
        self.maps_to_remember = int(config['maps_to_remember'])
        self.cmd = [config['zserv_exe'], '-waddir', self.waddir, '-iwad', self.iwad,
                    '-port', str(self.port), '-cfg', self.configfile, '-clog',
                    '-log']
        for wad in self.wads:
            self.cmd.extend(['-file', wad])
        ### other mandatory stuff
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

    def __str__(self):
        return "<ZServ [%s:%d]>" % (self.name, self.port)

    def initialize_stats(self):
        self.map = None
        self.red_team = self.team_class('red')
        self.blue_team = self.team_class('blue')
        self.green_team = self.team_class('green')
        self.white_team = self.team_class('white')
        self.teams = Dictable({'red': self.red_team,
                               'blue': self.blue_team,
                               'green': self.green_team,
                               'white': self.white_team})
        self.players = Dictable()
        self.disconnected_players = Dictable()

    def get_configuration(self):
        # TODO: add support for "add_mapnum_to_hostname"
        template = 'set cfg_activated "1"\n'
        template += 'set log_disposition "0"\n'
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

    def initialize_logs(self):
        connection_log_parser = ConnectionLogParser()
        general_log_parser = GeneralLogParser()
        self.connection_log = \
                        LogFile('connection', connection_log_parser, self)
        self.general_log = LogFile('general', general_log_parser, self)
        connection_log_filename = self.get_connection_log_filename()
        general_log_filename = self.get_general_log_filename()
        # if os.path.isfile(connection_log_filename):
        #     self.archive_connection_log()
        # if os.path.isfile(general_log_filename):
        #     self.archive_general_log()
        self.connection_log.set_filepath(self.get_connection_log_filename())
        self.general_log.set_filepath(self.get_general_log_filename())
        self.connection_log_listener = ConnectionLogListener(self)
        self.general_log_listener = GeneralLogListener(self)
        self.connection_log.listeners = [self.connection_log_listener]
        self.general_log.listeners = [self.general_log_listener]
        self.connection_log_listener.start()
        self.general_log_listener.start()
        self.connection_log.start()
        self.general_log.start()

    def archive_log(self, log_filename):
        # - check for log files
        # - if they exist
        #   - move all old-logs/$logfile.n to old-logs/$logfile.n+1
        #     - move $logfile to old-logs/$logfile.1
        log_basename = os.path.basename(log_filename)
        to_roll = []
        for old_log_file in os.listdir(self.old_log_dir):
            if old_log_file.startswith(log_basename):
                tokens = old_log_file.split('.')
                if tokens[-1].isdigit():
                    file_num = str(int(tokens[-1]) + 1)
                    tokens[-1] = file_num
                else:
                    file_num = '2'
                    tokens.append(file_num)
                old_log_path = os.path.join(self.old_log_dir, old_log_file)
                new_log_path = os.path.join(self.old_log_dir, '.'.join(tokens))
                to_roll.append((file_num, old_log_path, new_log_path))
        for n, olp, nlp in reversed(sorted(to_roll)):
            os.rename(olp, nlp)
        os.rename(log_filename, os.path.join(self.old_log_dir, log_basename))

    def archive_connection_log(self):
        self.archive_log(self.get_connection_log_filename())

    def archive_general_log(self):
        self.archive_log(self.get_general_log_filename())

    def spawn_zserv(self):
        while self.keep_spawning:
            self.log("Spawning [%s]" % (' '.join(self.cmd)))
            curdir = os.getcwd()
            os.chdir(self.homedir)
            self.zserv = Popen(self.cmd, stdin=PIPE, stdout=self.devnull,
                               bufsize=0, close_fds=True)
            self.pid = self.zserv.pid
            write_file(str(self.pid), self.pid_file)
            os.chdir(curdir)
            try:
                self.zserv.wait()
            except AttributeError: # can be raised during interpreter shutdown
                continue # skip all the rest of the stuff, shutting down
            self.save_current_stats()
            self.pid = None
            self.initialize_stats()
            self.initialize_logs()
            if os.path.isfile(self.pid_file):
                os.unlink(self.pid_file)
            # The zserv process has exited and we restart all over again

    def start(self):
        self.initialize_stats()
        self.initialize_logs()
        self.pid = None
        self.keep_spawning = True
        self.spawning_thread = start_thread(self.spawn_zserv)

    def stop(self, signum=15):
        self.keep_spawning = False
        if self.pid is not None:
            try:
                os.kill(self.pid, signum)
                out = True
            except Exception, e:
                es = "Caught exception while stopping: [%s]"
                self.log(es % (e))
                out = es % (e)
        # self.log("Joining spawning_thread")
        # self.spawning_thread.join()
        self.spawning_thread = None
        for logfile in self.general_log, self.connection_log:
            logfile.stop()
        for listener in self.general_log_listener, self.connection_log_listener:
            listener.stop()
        return out

    def restart(self, signum=15):
        self.stop(signum)
        self.start()

    def save_current_stats(self):
        if len(self.remembered_stats) == self.maps_to_remember:
            self.remembered_stats = Listable(self.remembered_stats[1:])
        if self.map:
            stats = Stats(self.map.export(), self.red_team.export(),
                          self.blue_team.export(), self.green_team.export(),
                          self.white_team.export(), self.players.export())
            ###
            # TODO:
            #   Don't remember maps where no one joined a game/team.
            ###
            self.remembered_stats.append(stats)

    def send_to_zserv(self, message):
        self.zserv.stdin.write(message)
        self.zserv.stdin.flush()

    def get_logfile_suffix(self, roll=False):
        now = datetime.now()
        today = datetime(now.year, now.month, now.day)
        if roll and now.hour == 23:
            today += timedelta(days=1)
        return today.strftime('-%Y%m%d') + '.log'

    def get_connection_log_filename(self, roll=False):
        return os.path.join(self.homedir, 'conn' + self.get_logfile_suffix())

    def get_general_log_filename(self, roll=False):
        return os.path.join(self.homedir, 'gen' + self.get_logfile_suffix())

    def add_player(self, player_name):
        ###
        # It's possible for players to have the same name, so that this
        # function will do nothing.  There's absolutely nothing we can do
        # about this, stats are just fucked for those players.  Basically, the
        # first player in line gets all the action.  In a way, it's funny
        # because a group of people could all join a server under the same
        # name, and blow up stats for a certain player.
        ###
        print "ZServ: add_player [%s]" % (player_name)
        player = self.player_class(player_name, self)
        if player.name not in self.players:
            self.players[player.name] = player
        else:
            if player.name in self.disconnected_players:
                del self.disconnected_players[player.name]
            self.players[player.name].disconnected = False

    def remove_player(self, player_name):
        player = self.player_class(player_name, self)
        if player.name in self.players:
            self.disconnected_players[player.name] = player
        self.players[player.name].disconnected = True

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

    def roll_log(self, log_file_name):
        if log_file_name == 'general':
            self.log("[%s] Rolling General Log" % (self.name))
            general_log_filename = self.get_general_log_filename(roll=True)
            s = "[%s]: New General LogFile: [%s]"
            self.log(s % (self.name, general_log_filename))
            self.general_log.set_filepath(general_log_filename)
        elif log_file_name == 'connection':
            self.log("[%s] Rolling Connection log" % (self.name))
            connection_log_filename = \
                                    self.get_connection_log_filename(roll=True)
            s = "[%s]: New Connection LogFile: [%s]"
            self.log(s % (self.name, connection_log_filename))
            self.general_log.set_filepath(connection_log_filename)
        else:
            es = "Received a log_roll event for non-existent log [%s]"
            self.log(es % (log_file_name))

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
        self.save_current_stats()
        self.map = self.map_class(map_number, map_name)
        for player_name, player in self.players.items():
            if player_name in self.disconnected_players:
                del self.players[player_name]
            else:
                player.initialize()
        self.disconnected_players = Dictable()
        for team in self.teams.values():
            team.initialize()
            team.set_map(self.map)

    def log_ip(self, player_name, player_ip):
        ###
        # We just instantiate the player, that object takes care of the
        # logging itself if an IP address is given.
        ###
        self.player_class(player_name, self, player_ip)

    def export(self):
        d = Dictable(
            {'name': self.name,
             'type': self.type,
             'port': self.port,
             'players': len(self.players) - len(self.disconnected_players),
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
             'max_teams': self.max_teams,
             'max_players_per_team': self.max_players_per_team,
             'teamdamage': self.teamdamage,
             'deathlimit': self.deathlimit,
             'timelimit': self.timelimit,
             'fraglimit': self.fraglimit,
             'scorelimit': self.scorelimit,
             'spam_window': self.spam_window,
             'spam_limit': self.spam_limit,
             'speed_check': self.speed_check,
             'restart_empty_map': self.restart_empty_map})
        if self.map:
            d['map'] = {'name': self.map.name, 'number': self.map.number,
                        'index': 0}
        d['remembered_stats'] = []
        counter = 0
        for rm in reversed(self.remembered_stats):
            counter += 1
            d['remembered_stats'].append({'name': rm.name, 'number': rm.number,
                                          'index': counter})
        return d.export()

