import os
from decimal import Decimal
from datetime import datetime
from subprocess import Popen, PIPE

from pyfileutils import write_file

from ZDStack import yes, no, start_thread, HOSTNAME, log
from ZDStack.Dictable import Dictable

class BaseZServ:

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
        self.log = lambda x: log('%s: %s' % (self.name, x))
        self.reload_config(config)
        self.pid = None
        self.pre_spawn_funcs = []
        self.post_spawn_funcs = []
        self.extra_exportables_funcs = []

    def reload_config(self, config):
        self.log("BaseZServ: reload_config")
        self.load_config(config)
        self.configuration = self.get_configuration()
        write_file(self.configuration, self.configfile, overwrite=True)

    def load_config(self, config):
        self.log("BaseZServ: load_config")
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
            wads = [x.strip() for x in config['wads'].split(',')]
            for wad in wads:
                wadpath = os.path.join(config['waddir'], wad)
                if not os.path.isfile(wadpath):
                    raise ValueError("WAD [%s] not found" % (wad))
            self.wads = wads
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
        self.max_clients = None
        self.max_players = None
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
            self.maps = [x.strip() for x in config['maps'].split(',') if x]
        if is_valid('optional_wads'):
            self.optional_wads = \
                [x.strip() for x in config['optional_wads'].split(',') if x]
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
        if is_valid('dmflags'):
            self.dmflags = config['dmflags']
        elif is_valid(self.type + '_dmflags'):
            self.dmflags = config[self.type + '_dmflags']
        if is_valid('dmflags2'):
            self.dmflags2 = config['dmflags2']
        elif is_valid(self.type + '_dmflags2'):
            self.dmflags2 = config[self.type + '_dmflags2']
        if is_valid('max_clients'):
            self.max_clients = int(config['max_clients'])
        elif is_valid(self.type + '_max_clients'):
            self.max_clients = int(config[self.type + '_max_clients'])
        if is_valid('max_players'):
            self.max_players = int(config['max_players'])
        elif is_valid(self.type + '_max_players'):
            self.max_players = int(config[self.type + '_max_players'])
        if is_valid('timelimit'):
            self.timelimit = int(config['timelimit'])
        elif is_valid(self.type + '_timelimit'):
            self.timelimit = int(config[self.type + '_timelimit'])
        config['name'] = self.name
        config['dmflags'] = self.dmflags
        config['dmflags2'] = self.dmflags2
        config['max_clients'] = self.max_clients
        config['max_players'] = self.max_players
        config['timelimit'] = self.timelimit
        self.config = config

    def __str__(self):
        return "<ZServ [%s:%d]>" % (self.name, self.port)

    def get_configuration(self):
        self.log("BaseZServ: get_configuration")
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
        if self.max_clients:
            template += 'set maxclients "%s"\n' % (self.max_clients)
        if self.max_players:
            template += 'set maxplayers "%s"\n' % (self.max_players)
        if self.timelimit:
            template += 'set timelimit "%s"\n' % (self.timelimit)
        if self.fraglimit:
            template += 'set fraglimit "%s"\n' % (self.fraglimit)
        return template # % self.config

    def spawn_zserv(self):
        self.log("BaseZServ: spawn_zserv")
        while self.keep_spawning:
            self.log("Spawning [%s]" % (' '.join(self.cmd)))
            self.zdstack.spawn_lock.acquire()
            curdir = os.getcwd()
            os.chdir(self.homedir)
            for func, args, kwargs in self.pre_spawn_funcs:
                func(*args, **kwargs)
            self.zserv = Popen(self.cmd, stdin=PIPE, stdout=self.devnull,
                               bufsize=0, close_fds=True)
            self.pid = self.zserv.pid
            write_file(str(self.pid), self.pid_file)
            os.chdir(curdir)
            self.zdstack.spawn_lock.release()
            try:
                self.zserv.wait()
            except:      # can be raised during interpreter shutdown
                try:
                    if os.path.isfile(self.pid_file):
                        os.unlink(self.pid_file)
                except:
                    pass
                continue # shutting down, skip the post_spawn stuff
            for func, args, kwargs in self.post_spawn_funcs:
                func(*args, **kwargs)
            self.clean_up_after_zserv()
            # The zserv process has exited and we restart all over again

    def clean_up_after_zserv(self):
        self.log("BaseZServ: clean_up_after_zserv")
        self.pid = None
        if os.path.isfile(self.pid_file):
            os.unlink(self.pid_file)

    def start(self):
        self.log("BaseZServ: start")
        self.pid = None
        self.keep_spawning = True
        self.spawning_thread = start_thread(self.spawn_zserv,
                                            "%s spawning thread" % (self.name))

    def stop(self, signum=15):
        self.log("BaseZServ: stop")
        self.keep_spawning = False
        if self.pid is not None:
            try:
                os.kill(self.pid, signum)
                out = True
            except Exception, e:
                es = "Caught exception while stopping: [%s]"
                self.log(es % (e))
                out = es % (e)
        self.spawning_thread = None
        return out

    def restart(self, signum=15):
        self.log("BaseZServ: restart")
        self.stop(signum)
        self.start()

    def send_to_zserv(self, message):
        self.log("BaseZServ: send_to_zserv")
        self.zserv.stdin.write(message)
        self.zserv.stdin.flush()

    def export(self):
        self.log("BaseZServ: export")
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
        for func, args, kwargs in self.extra_exportables_funcs:
            d = func(*([d] + args), **kwargs)
        return Dictable(d).export()

