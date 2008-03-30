from ZDStack import get_configparser

from ZDStack.Team import Team
from ZDStack.Listable import Listable
from ZDStack.Server import Server

class ZDStack(Server):

    def __init__(self, name):
        Server.__init__(self, name, get_configparser())
        self.start_time = datetime.now()
        self.red_team = Team('Red')
        self.blue_team = Team('Blue')
        self.green_team = Team('Green')
        self.white_team = Team('White')
        self.players = Listable()
        self.keep_spawning = Event()
        # self.register()
        self.zserv_pid = None
        self.connection_log = None
        self.general_log = None
        self.weapon_log = None

    def load_config(self):
        self.base_iwad = self.config['iwad']
        self.iwad = os.path.join(self.iwaddir, self.base_iwad)
        if not os.path.isfile(self.iwad):
            raise ValueError("Could not find IWAD %s" % (self.iwad))
        self.waddir = self.config['waddir']
        if not os.path.isdir(self.waddir):
            raise ValueError("WAD dir %s is not valid" % (self.waddir))
        self.iwaddir = self.config['iwaddir']
        if not os.path.isdir(self.iwaddir):
            raise ValueError("IWAD dir %s is not valid" % (self.waddir))
        self.wads = self.config['wads'].split(',')
        self.wads = [os.path.join(self.waddir, x) for x in self.wads if x]
        for wad in self.wads:
            if not os.path.isfile(wad):
                raise ValueError("WAD %s not found" % (wad))
        self.rcon_password = self.config['rcon']
        self.server_password = self.config['password']
        if not self.server_password:
            self.requires_password = '0'
        else:
            self.requires_password = '1'
        self.advertise = self.config['advertise']
        self.motd = self.config['motd']
        self.teamdamage = self.config['teamdamage']
        self.timelimit = self.config['timelimit']
        self.port = int(self.config['port'])
        self.maps = [x for x in self.config['maps'].split(',') if x]
        self.type = self.config['type']
        d = {}
        d['name'] = self.name
        d['master_advertise'] = self.advertise
        d['motd'] = self.motd
        d['teamdamage'] = self.teamdamage
        d['rcon_password'] = self.rcon_password
        d['maps'] = '\n'.join(['addmap "%s"' % (x) for x in self.maps])
        d['hostname'] = self.hostname
        d['optional_wads'] = ' '.join(self.config['optional_wads'].split(','))
        d['optional_wads'] = 'set optional wads "%s"' % (d['optional_wads'])
        if self.server_password:
            d['requires_password'] = '1'
            d['server_password'] = 'set password "%s"' % (self.server_password)
        else:
            d['requires_password'] = '0'
            d['server_password'] = ''
        if self.type in ('ctf', 'teamdm'):
            d['deathmatch'] = '1'
            d['teamplay'] = '1'
            fraglimit_option = None
            if self.type == 'ctf':
                d['ctf'] = '1'
                dmflags_option = 'ctf_dmflags'
                dmflags2_option = 'ctf_dmflags2'
                max_clients_option = 'ctf_max_clients'
                max_players_option = 'ctf_max_players'
                scorelimit_option = 'ctf_score_limit'
                max_teams_option = 'ctf_max_teams'
                max_players_per_team_option = 'ctf_max_players_per_team'
            elif self.type == 'teamdm':
                d['ctf'] = '0'
                dmflags_option = 'teamdm_dmflags'
                dmflags2_option = 'teamdm_dmflags2'
                max_clients_option = 'teamdm_max_clients'
                max_players_option = 'teamdm_max_players'
                scorelimit_option = 'teamdm_score_limit'
                max_teams_option = 'teamdm_max_teams'
                max_players_per_team_option = 'teamdm_max_players_per_team'
        elif self.type in ('1-on-1', 'duel', 'ffa', 'coop'):
            d['teamplay'] = '0'
            d['ctf'] = '0'
            d['timelimit'] = ''
            scorelimit_option = None
            max_teams_option = None
            max_players_per_team_option = None
            if self.type == '1-on-1' or self.type == 'duel':
                d['deathmatch'] = '1'
                dmflags_option = '1on1_dmflags'
                dmflags2_option = '1on1_dmflags2'
                max_clients_option = '1on1_max_clients'
                max_players_option = '1on1_max_players'
                frag_limit_option = '1on1_fraglimit'
            elif self.type == 'ffa':
                d['deathmatch'] = '1'
                dmflags_option = 'ffa_dmflags'
                dmflags2_option = 'ffa_dmflags2'
                max_clients_option = 'ffa_max_clients'
                max_players_option = 'ffa_max_players'
                frag_limit_option = 'ffa_fraglimit'
            elif self.type == 'coop':
                d['deathmatch'] = '0'
                dmflags_option = 'coop_dmflags'
                dmflags2_option = 'coop_dmflags2'
                max_clients_option = 'coop_max_clients'
                max_players_option = 'coop_max_players'
                frag_limit_option = None
        else:
            raise ValueError("Unsupported server type: %s" % (self.type))
        server_options = ('dmflags', 'dmflags2', 'max_players_per_team',
                          'max_clients', 'max_players', 'max_teams',
                          'fraglimit')
        type_options = (dmflags, dmflags2, max_players_per_team_option,
                        max_clients_option, max_players_option,
                        max_teams_option, fraglimit_option)
        for server_option, type_option in zip(server_options, type_options):
            if server_option in self.config:
                d[server_option] = self.config[server_option]
            elif type_option is not None:
                d[server_option] = self.config[type_option]
            else:
                d[server_option] = ''
        write_file(read_file(template) % d, self.configfile, overwrite=True)
        self.cmd = [ZSERV_EXE, '-noinput', '-waddir', self.waddir, '-iwad',
                    self.iwad, '-port', str(self.port), '-cfg',
                    self.configfile, '-clog', '-wlog']
        for wad in self.wads:
            self.cmd.extend(['-file', wad])
        self.address = 'http://%s:%d' % (HOSTNAME, self.port)

    def start_zserv(self):
        while 1:
            self.keep_spawning.wait()
            self.log("Spawning [%s]" % (' '.join(self.cmd)))
            print "Spawning [%s]" % (' '.join(self.cmd))
            self.zserv_pid = os.spawnv(os.P_NOWAIT, self.cmd[0], self.cmd)
            self.connection_log = LogFile(self.get_connection_log_file(),
                                          'connection', ConnectionLineParser())
            self.general_log = LogFile(self.get_general_log_file(),
                                          'general', GeneralLineParser())
            self.weapon_log = LogFile(self.get_weapon_log_file(),
                                      'weapon', WeaponLineParser())
            print "Waiting on [%d]" % (self.zserv_pid)
            os.waitpid(self.zserv_pid, 0)
            print "Served exited, clearing zserv_pid"
            self.zserv_pid = None
            self.connection_log = None
            self.general_log = None
            self.weapon_log = None

    def stop_zserv(self, signum=15):
        try:
            print "Sending signal %s to %s PID: %s" % (signum, self.name, self.zserv_pid)
            os.kill(self.zserv_pid, signum)
            return True
        except Exception, e:
            es = str(e)
            self.log(es)
            return es

    def startup(self):
        Server.startup(self)
        self.start_zserv()

    def shutdown(self):
        self.stop_serving()
        self.stop()
        self.log("Deleting PID file %s" % (self.pidfile))
        delete_file(self.pidfile)
        if self.zserv_pid is not None:
            print "Stopping running zserv process"
            self.stop_zserv(signum=signum)
        sys.exit(0)

    def add_player(self, player):
        self.players.append(player)

    def remove_player(self, player):
        self.players.remove(player)

    def get_player(self, player_name):
        ###
        # It's possible for players to have the same name, so that this
        # list comprehension will return more than 1 name.  There's absolutely
        # nothing we can do about this, stats are just fucked for those
        # players.  Basically, the first player in line gets all the action.
        ###
        players = [x for x in self.players if x.player_name == player_name]
        if not len(players):
            return None
        return players[0]

    def handle_message(self, message, possible_player_names):
        ###
        #
        # I think the way this will work is we will check the messager's
        # homogenized name against some list of messagers and regexp pairs.
        # Then, we can take a specific action like "kick" or "say".  So,
        # something like:
        #
        # mionicd: "^no$" kick
        #
        ###
        player_names = dict([(x.name, x) for x in self.players])
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

    def handle_rcon_denied(self, player_name):
        player = self.get_player(player_name)
        if player is None:
            es = "Received an RCON denial for a non-existant player [%s]!"
            self.log(es % (player_name))
        else:
            player.rcon_denials += 1

    def handle_rcon_granted(self, player_name):
        player = self.get_player(player_name)
        if player is None:
            es = "Received an RCON access for a non-existant player [%s]!"
            self.log(es % (player_name))
        else:
            player.rcon_accesses += 1

    def handle_rcon_action(self, player_name):
        player = self.get_player(player_name)
        if player is None:
            es = "Received an RCON action for a non-existant player [%s]!"
            self.log(es % (player_name))
        else:
            player.rcon_actions += 1
