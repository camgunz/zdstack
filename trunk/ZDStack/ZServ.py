from __future__ import with_statement

import os
import time

from decimal import Decimal
from datetime import date, datetime, timedelta
from threading import Timer, Lock, Event
from subprocess import Popen, PIPE, STDOUT

from ZDStack import DEVNULL, TICK, TEAM_COLORS, PlayerNotFoundError, \
                    get_zdslog, get_plugins
from ZDStack.ZDSTask import Task
from ZDStack.ZDSModels import Round
from ZDStack.ZDSDatabase import get_port, get_game_mode, get_map, get_round, \
                                get_round_by_id, get_alias, persist, \
                                global_session
from ZDStack.ZDSTeamsList import TeamsList
from ZDStack.ZDSPlayersList import PlayersList
from ZDStack.ZDSZServConfig import ZServConfigParser

COOP_MODES = ('coop', 'cooperative', 'co-op', 'co-operative')
DUEL_MODES = ('1v1', 'duel', '1vs1')
FFA_MODES = ('ffa', 'deathmatch', 'dm', 'free for all', 'free-for-all')
TEAMDM_MODES = ('teamdm', 'team deathmatch', 'tdm')
CTF_MODES = ('ctf', 'capture the flag', 'capture-the-flag')
DM_MODES = DUEL_MODES + FFA_MODES + TEAMDM_MODES + CTF_MODES
TEAM_MODES = TEAMDM_MODES + CTF_MODES

zdslog = get_zdslog()

class ZServ(object):

    """ZServ provides an interface to a zserv process.

    ZServ does the following:

      * Handles configuration of the zserv process
      * Provides control over the zserv process
      * Provides a method to communicate with the zserv process
      * Exports server configuration information

    """

    source_port = 'zdaemon'

    def __init__(self, name, zdstack):
        """Initializes a ZServ instance.

        name:      a string representing the name of this ZServ.
        zdstack:   the calling (ZD)Stack instance.

        """
        self.start_time = datetime.now()
        self.restarts = list()
        self.name = name
        self.zdstack = zdstack
        self._fragment = None
        self.event_type_to_watch_for = None
        self.response_events = list()
        self.response_finished = Event()
        self.finished_processing_response = Event()
        self.state_lock = Lock()
        self._zserv_stdin_lock = Lock()
        self.config_lock = Lock()
        self.ban_timers = set()
        self.ban_timer_lock = Lock()
        self.round_id = None
        self.players = PlayersList(self)
        self.teams = TeamsList(self)
        self.players_holding_flags = list()
        self.teams_holding_flags = list()
        self.fragged_runners = list()
        self.team_scores = dict()
        self._template = ''
        self.zserv = None
        self.fifo = None
        self.config = ZServConfigParser(self)
        self.load_config()
        self.clear_state()
        if self.events_enabled and self.plugins_enabled:
            plugin_names = self.config.getlist('plugins', default=list())
            zdslog.debug("Plugin names: %s" % (plugin_names))
            self.plugins = get_plugins(plugin_names)
            zdslog.debug("Plugins: %s" % (self.plugins))
        else:
            zdslog.debug("Events enabled, plugins enabled: %s, %s" % (self.events_enabled, self.plugins_enabled))
            self.plugins = list()

    def clear_state(self):
        """Clears the current state of the round."""
        with self.state_lock:
            self.players.clear()
            self.teams.clear()
            self.players_holding_flags = list()
            self.teams_holding_flags = list()
            self.fragged_runners = list()
            if self.playing_colors:
                self.team_scores = dict(zip(self.playing_colors,
                                            [0] * len(self.playing_colors)))
            else:
                self.team_scores = dict()

    def clean_up(self):
        """Cleans up after a round."""
        zdslog.debug('Cleaning up')
        now = datetime.now()
        if not self.round_id:
            zdslog.debug("self.round_id: [%s]" % (self.round_id))
            return
        with global_session() as session:
            round = get_round_by_id(self.round_id, session=session)
            if self.stats_enabled:
                zdslog.debug("Setting round end_time to [%s]" % (now))
                round.end_time = now
                s = "Adding %s to %s"
                for p in self.players:
                    a = get_alias(p.name, p.ip, round=round, session=session)
                    if round not in a.rounds:
                        zdslog.debug(s % (round, a))
                        a.rounds.append(round)
                zdslog.debug("Updating %s" % (round))
                persist(round, update=True, session=session)
                for flag_touch in round.flag_touches:
                    ###
                    # Players can hold flags until a round ends, thus the
                    # FlagTouch will never have a loss_time.  Technically,
                    # however, the loss_time would be at the end of a round,
                    # because you can't hold a flag when there is no round.
                    ###
                    zdslog.debug("Checking that %s has a loss_time")
                    if not flag_touch.loss_time:
                        flag_touch.loss_time = now
                        zdslog.debug("Updating %s" % (flag_touch))
                        persist(flag_touch, update=True, session=session)
            else:
                ###
                # Because statistics are not enabled, all generated stats must
                # be deleted at the conclusion of a round.  Not everything is
                # deleted.  Some things we want to persist, like weapons, team
                # colors, ports, game modes and maps.  This stuff shouldn't
                # take up too much memory anyway.  The rest of the stuff, like
                # stats & aliases, can go out the window.
                ###
                zdslog.debug("Deleting a bunch of stuff")
                for stat in round.players + \
                            round.frags + \
                            round.flag_touches + \
                            round.flag_returns + \
                            round.rcon_accesses + \
                            round.rcon_denials + \
                            round.rcon_actions:
                    zdslog.debug("Deleting %s" % (stat))
                    session.delete(stat)
                zdslog.debug("Deleting %s" % (round))
                session.delete(round)
        self.round_id = None
        self.clear_state()

    def get_round(self, session=None):
        """Gets this ZServ's current Round.

        :param session: the session to use, if none is given, the
                        global session is used
        :type session: Session
        :rtype: :class:`~ZDStack.ZDSModels.Round`
        :returns: the current Round or None

        """
        if self.round_id:
            return get_round_by_id(self.round_id, session=session)

    def get_map(self, session=None):
        """Gets this ZServ's current Map.

        :param session: the session to use, if none is given, the
                        global session is used
        :type session: Session
        :rtype: :class:`~ZDStack.ZDSModels.Map`
        :returns: the current Map or None

        """
        if self.map_number and self.map_name:
            return get_map(number=self.map_number, name=self.map_name)

    def get_game_mode(self, session=None):
        """Gets this ZServ's current GameMode.

        :param session: the session to use, if none is given, the
                        global session is used
        :type session: Session
        :rtype: :class:`~ZDStack.ZDSModels.GameMode`
        :returns: the current GameMode

        """
        return get_game_mode(name=self.game_mode,
                             has_teams=self.game_mode in TEAM_MODES)

    def get_source_port(self, session=None):
        """Gets this ZServ's current (source) Port.

        :param session: the session to use, if none is given, the
                        global session is used
        :type session: Session
        :rtype: :class:`~ZDStack.ZDSModels.Port`
        :returns: the current (source) Port

        """
        return get_port(name=self.source_port)

    def change_map(self, map_number, map_name):
        """Handles a map change event.

        :param map_number: the number of the new map
        :type map_number: int
        :param map_name: the name of the new map
        :type map_name: string

        """
        zdslog.debug('Change Map')
        self.clean_up()
        self.map_number = map_number
        self.map_name = map_name
        self.round_id = get_round(self.get_game_mode(), self.get_map()).id
        zdslog.debug('%s Round ID: [%s]' % (self.name, self.round_id))
        ###
        # Because there are no player reconnections at the beginning of rounds
        # in 1.08.08, we need to manually do a sync() here.
        ###
        self.players.sync()

    def reload_config(self):
        """Reloads the config for the ZServ.

        config: a RawZDSConfigParser instance or subclass.

        """
        # zdslog.debug('')
        self.load_config(reload=True)

    def load_config(self, reload=False):
        """Loads this ZServ's config.

        reload: an optional that, if True, reloads the config.  False
                by default.

        """
        with self.config_lock:
            # zdslog.debug('')
            self.config.process_config() # does tons of ugly, ugly stuff
            gm = self.get_game_mode()
            source_port = self.get_source_port()
            if gm not in source_port.game_modes:
                source_port.game_modes.append(gm)
                persist(source_port, update=True)
            if source_port not in gm.ports:
                gm.ports.append(source_port)
                persist(gm, update=True)
            if not reload and not self.is_running():
                if os.path.exists(self.fifo_path):
                    ###
                    # Re-create the FIFO so we know there are no mode problems,
                    # and that it's definitely a FIFO.
                    ###
                    os.remove(self.fifo_path)
                b = [x for x in os.listdir(self.home_folder)]
                for x in [x for x in b if x.endswith('.log')]:
                    p = os.path.join(self.home_folder, x)
                    try:
                        if os.path.isfile(p) or os.path.islink(p):
                            os.remove(p)
                        else:
                            es = "%s: Cannot start, cannot remove old log file"
                            es += " %s"
                            raise Exception(es % (self.name, p))
                    except Exception, e:
                        if 'Cannot start, cannot remove old log file' in str(e):
                            es = "%s: " + str(e)
                            raise Exception(es % (self.name))
                        else:
                            raise
            if not os.path.exists(self.fifo_path):
                os.mkfifo(self.fifo_path)

    def __str__(self):
        return "<ZServ [%s:%d]>" % (self.name, self.port)

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
        # zdslog.debug('Poll: %s' % (x))
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
            loglink_path = os.path.join(self.home_folder, loglink_name)
            if os.path.exists(loglink_path):
                if not os.path.islink(loglink_path):
                    es = "Cannot create log link, something named %s that is "
                    es += "not a link already exists"
                    raise Exception(es % (loglink_path))
            else:
                # s = "Linking %s to %s"
                # zdslog.debug(s % (loglink_path, self.fifo_path))
                os.symlink(self.fifo_path, loglink_path)

    def start(self):
        """Starts the zserv process.
        
        This keeps a reference to the running zserv process in
        self.zserv.
        
        """
        # zdslog.debug('Acquiring spawn lock [%s]' % (self.name))
        with self.config_lock:
            with self.zdstack.spawn_lock:
                if self.is_running():
                    return
                self.restarts.append(datetime.now())
                fobj = open(self.configfile, 'w')
                fobj.write(self.config.get_config_data())
                fobj.flush()
                fobj.close()
                self.ensure_loglinks_exist()
                if self.plugins_enabled:
                    for plugin in self.plugins:
                        zdslog.info("Loaded plugin [%s]" % (plugin))
                else:
                    pass
                    # zdslog.info("Not loading plugins")
                ###
                # Should we do something with STDERR here?
                ###
                ###
                # Due to the semi-complicated blocking structure of FIFOs,
                # there is a specific order in which this has to be done.
                #
                #   - Writing to a FIFO blocks until there is something
                #     listening, so self.zdstack.polling_thread has to be
                #     spawned.
                #   - The polling thread only handles ZServs with .fifo
                #     attributes that are non-False, so self.fifo has to be
                #     created.
                #   - Then the zserv can be spawned.
                ###
                zdslog.info("Spawning zserv [%s]" % (' '.join(self.cmd)))
                self.fifo = os.open(self.fifo_path, os.O_RDONLY | os.O_NONBLOCK)
                self.zserv = Popen(self.cmd, stdin=PIPE, stdout=DEVNULL,
                                   stderr=STDOUT, bufsize=0, close_fds=True,
                                   cwd=self.home_folder)
                # self.send_to_zserv('players') # avoids CPU spinning

    def stop(self, check_if_running=True, signum=15):
        """Stops the zserv process.

        :param check_if_running: whether or not to check if the
                                 internal zserv process is running
        :type check_if_running: boolean
        :param signum: the signal number to send to the zserv process,
                       15 (SIGTERM) by default
        :type signum: int

        """
        is_running = self.is_running()
        if not check_if_running or is_running:
            error_stopping = False
            zdslog.debug("Killing zserv process")
            if is_running:
                zdslog.debug("Ban Timers: %s" % (str(self.ban_timers)))
                ###
                # We don't want timed bans to become permanent, so we unban
                # all temporarily banned players here.
                ###
                with self.ban_timer_lock:
                    for ban_timer in self.ban_timers:
                        ds = "Cancelling ban timer [%s]"
                        zdslog.debug(ds % (ban_timer))
                        ban_timer.cancel()
                        self.zkillban(ban_timer.args[0])
                    self.ban_timers = set()
                try:
                    os.kill(self.zserv.pid, signum)
                    ###
                    # Python docs say to use communicate() to avoid a wait()
                    # deadlock due to buffers being full.  Because we're
                    # redirecting both STDOUT and STDERR to DEVNULL, nothing
                    # will come from this.  Apparently we still need to do it
                    # though....
                    ###
                    self.zserv.communicate()   # returns (None, None)
                    retval = self.zserv.wait() # we don't actually use this
                except Exception, e:
                    es = "Caught exception while stopping: [%s]" % (e)
                    zdslog.error(es)
                    error_stopping = es
            os.close(self.fifo)
            self.fifo = None
            self.zserv = None
            self.clean_up()
            return error_stopping
        else:
            raise Exception("[%s] already stopped" % (self.name))

    def restart(self, signum=15):
        """Restarts the zserv process, restarting it if it crashes.

        signum: an int representing the signal number to send to the
                zserv process.  15 (TERM) by default.

        """
        zdslog.debug('')
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
        # zdslog.debug('')
        if '\n' in message or '\r' in message:
            es = "Message cannot contain newlines or carriage returns"
            raise ValueError(es)
        def _send(message):
            zdslog.debug("Writing to STDIN")
            self.zserv.stdin.write(message + '\n')
            self.zserv.stdin.flush()
        zdslog.debug("Obtaining STDIN lock")
        with self._zserv_stdin_lock:
            zdslog.debug("Obtained STDIN lock")
            ###
            # zserv's STDIN is (obviously) not threadsafe, so we need to ensure
            # that access to it is limited to 1 thread at a time, which is both
            # writing to it, and waiting for responses from its STDOUT.
            ###
            if not self.events_enabled or event_response_type is None:
                return _send(message)
            zdslog.debug("Setting response type")
            self.response_events = []
            self.event_type_to_watch_for = event_response_type
            self.response_finished.clear()
            _send(message)
            response = []
            zdslog.debug("Waiting for response")
            ###
            # In case a server is restarted before a non-response event occurs,
            # we need a timeout here.
            ###
            self.response_finished.wait(float(TICK*4))
            ###
            # We want to process this response before any other events, so make
            # other threads wait until we're finished processing the response.
            ###
            self.finished_processing_response.clear()
            try:
                zdslog.debug("Processing response events")
                for event in self.response_events:
                    d = {'type': event.type, 'line': event.line}
                    d.update(event.data)
                    response.append(d)
                zdslog.debug("Send to ZServ response: [%s]" % (response))
                return response
            finally:
                zdslog.debug("Clearing response state")
                self.response_events = []
                self.event_type_to_watch_for = None
                zdslog.debug("Setting response processing finished")
                self.finished_processing_response.set()
                self.response_finished.set()

    def zaddban(self, ip_address, reason='rofl'):
        """Adds a ban.

        ip_address: a string representing the IP address to ban
        reason:     a string representing the reason for the ban

        """
        # zdslog.debug('')
        return self.send_to_zserv('addban %s %s' % (ip_address, reason),
                                  'addban_command')

    def zaddtimedban(self, duration, ip_address, reason='rofl'):
        """Adds a ban with an expiration.

        duration:   an integer representing how many minutes the ban
                    should last
        ip_address: a string representing the IP address to ban
        reason:     a string representing the reason for the ban

        """
        zdslog.debug("Adding timed ban for [%s]" % (ip_address))
        self.zaddban(ip_address, reason)
        args = [ip_address]
        t = Timer(duration * 60, self.remove_timed_ban, args)
        args.append(t)
        self.ban_timers.add(t)
        t.start()
        zdslog.debug("Ban Timers: %s" % (str(self.ban_timers)))

    def remove_timed_ban(self, ip_address, timer):
        """Removes a temporary ban.

        :param ip_address: the IP address to unban
        :type ip_address: string
        :param timer: the ban timer that called this method
        :type timer: threading.Timer

        """
        with self.ban_timer_lock:
            if not timer.isAlive():
                return
            self.zkillban(ip_address)
            self.ban_timers.remove(timer)

    def zaddbot(self, bot_name):
        """Adds a bot.

        bot_name: a string representing the name of the bot to add.

        """
        # zdslog.debug('')
        return self.send_to_zserv('addbot %s' % (bot_name), 'addbot_command')

    def zaddmap(self, map_number):
        """Adds a map to the maplist.

        map_number: an int representing the name of the map to add

        """
        # zdslog.debug('')
        return self.send_to_zserv('addmap %s' % (map_number))

    def zclearmaplist(self):
        """Clears the maplist."""
        # zdslog.debug('')
        return self.send_to_zserv('clearmaplist')

    def zget(self, variable_name):
        """Gets a variable.

        variable_name: a string representing the name of the variable
                       to get

        """
        # zdslog.debug('')
        return self.send_to_zserv('get %s', 'get_command')

    def zkick(self, player_number, reason='rofl'):
        """Kicks a player.

        player_number: an int representing the number of the player to
                       kick
        reason:        a string representing the reason for the kick

        """
        # zdslog.debug('')
        return self.send_to_zserv('kick %s %s' % (player_number, reason))

    def zkillban(self, ip_address):
        """Removes a ban.

        ip_address: a string representing the IP address to un-ban

        """
        # zdslog.debug('')
        return self.send_to_zserv('killban %s' % (ip_address))

    def zmap(self, map_number):
        """Changes the current map.

        map_number: an int representing the number of the map to
                    change to

        """
        # zdslog.debug('')
        return self.send_to_zserv('map %s' % (map_number))

    def zmaplist(self):
        """Gets the maplist.

        Returns a list of strings representing the names of maps in
        the maplist.  An example of one of these strings is: "map01".

        """
        # zdslog.debug('')
        return self.send_to_zserv('maplist', 'maplist_command')

    def zplayers(self):
        """Returns a list of players in the server."""
        # zdslog.debug('')
        return self.send_to_zserv('players', 'players_command')

    def zremovebots(self):
        """Removes all bots."""
        # zdslog.debug('')
        return self.send_to_zserv('removebots')

    def zresetscores(self):
        """Resets all scores."""
        # zdslog.debug('')
        return self.send_to_zserv('resetscores')

    def zsay(self, message):
        """Sends a message as ] CONSOLE [.
        
        message: a string representing the message to send.
        
        """
        # zdslog.debug('')
        return self.send_to_zserv('say %s' % (message))

    def zset(self, variable_name, variable_value):
        """Sets a variable.

        variable_name:  a string representing the name of the variable
                        to set
        variable_value: a string representing the value to set the
                        variable to

        """
        # zdslog.debug('')
        s = 'set %s "%s"' % (variable_name, variable_value)
        return self.send_to_zserv(s)

    def ztoggle(self, boolean_variable):
        """Toggles a boolean variable.

        boolean_variable: a string representing the name of the
                          boolean variable to toggle

        """
        # zdslog.debug('')
        return self.send_to_zserv('toggle %s' % (boolean_variable))

    def zunset(self, variable_name):
        """Unsets a variable.

        variable_name: a string representing the name of the variable
                       to unset

        """
        # zdslog.debug('')
        return self.send_to_zserv('unset %s' % (variable_name))

    def zwads(self):
        """Returns a list of the wads in use."""
        # zdslog.debug('')
        return self.send_to_zserv('wads', 'wads_command')

