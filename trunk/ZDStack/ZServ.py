from __future__ import with_statement

import os
import time

from decimal import Decimal
from datetime import date, datetime, timedelta
from threading import Timer, Lock, Event
from subprocess import Popen, PIPE, STDOUT

from ZDStack import DEVNULL, TICK, TEAM_COLORS, PlayerNotFoundError, \
                    get_zdslog, get_plugins

COOP_MODES = ('coop', 'cooperative', 'co-op', 'co-operative')
DUEL_MODES = ('1v1', 'duel', '1vs1')
FFA_MODES = ('ffa', 'deathmatch', 'dm', 'free for all', 'free-for-all')
TEAMDM_MODES = ('teamdm', 'team deathmatch', 'tdm')
CTF_MODES = ('ctf', 'capture the flag', 'capture-the-flag')
DM_MODES = DUEL_MODES + FFA_MODES + TEAMDM_MODES + CTF_MODES
TEAM_MODES = TEAMDM_MODES + CTF_MODES
NUMBERS_TO_COLORS = {0: 'red', 1: 'blue', 2: 'green', 3: 'white'}
COLORS_TO_NUMBERS = {'red': 0, 'blue': 1, 'green': 2, 'white': 3}

from ZDStack.ZDSTask import Task
from ZDStack.ZDSModels import Round, GameMode, Port, Map, Alias
from ZDStack.ZDSDatabase import requires_session, global_session
from ZDStack.ZDSPlayersList import PlayersList
from ZDStack.ZDSZServConfig import ZServConfigParser
from ZDStack.ZDSZServAccessList import ZServAccessList

from sqlalchemy.orm.exc import NoResultFound

zdslog = get_zdslog()

class ZServ(object):

    """ZServ provides an interface to a zserv process.

    .. attribute:: start_time
        A datetime representing the time this ZServ was started - or
        None if it is currently stopped.

    .. attribute:: restarts
        A list of datetimes representing the times of the last 2
        restarts (at the most).

    .. attribute:: name
        A string representing the name of the ZServ.

    ZServ does the following:

      * Handles configuration of the zserv process
      * Provides control over the zserv process
      * Provides a method to communicate with the zserv process
      * Exports server configuration information

    """

    source_port = 'zdaemon'

    def __init__(self, name, zdstack):
        """Initializes a ZServ instance.

        :param name: the name of this ZServ
        :type name: string
        :param zdstack: the calling (ZD)Stack instance
        :type zdstack: :class:`~ZDStack.Stack`

        """
        self.start_time = None
        self.restarts = list()
        self.map_name = None
        self.map_number = None
        self.round_id = None
        self.name = name
        self.zdstack = zdstack
        self._fragment = None
        self.event_type_to_watch_for = None
        self.response_events = list()
        self.response_finished = Event()
        self.finished_processing_response = Event()
        self.whitelist_lock = Lock()
        self.event_lock = Lock()
        self.state_lock = Lock()
        self._zserv_stdin_lock = Lock()
        self.config_lock = Lock()
        self.ban_timers = set()
        self.ban_timer_lock = Lock()
        self.round_id = None
        self.players = PlayersList(self)
        self.players_holding_flags = set()
        self.teams_holding_flags = set()
        self.fragged_runners = list()
        self.team_scores = dict()
        self._template = ''
        self.zserv = None
        self.fifo = None
        self.config = ZServConfigParser(self)
        self.access_list = ZServAccessList(self)
        self.load_config()
        self.clear_state()
        if self.events_enabled and self.plugins_enabled:
            plugin_names = self.config.getlist('plugins', default=list())
            zdslog.debug("Plugin names: %s" % (plugin_names))
            self.plugins = get_plugins(plugin_names)
            loaded_plugin_names = [x.__name__ for x in self.plugins]
            for y in [x for x in plugin_names if x not in loaded_plugin_names]:
                zdslog.error("Plugin %s not found" % (y))
            zdslog.debug("Plugins: %s" % (self.plugins))
        else:
            ds = "Events enabled, plugins enabled: %s, %s"
            zdslog.debug(ds % (self.events_enabled, self.plugins_enabled))
            self.plugins = list()

    def clear_state(self):
        """Clears the current state of the round."""
        with self.state_lock:
            self.players.clear(acquire_lock=False)
            self.players_holding_flags = set()
            self.teams_holding_flags = set()
            self.fragged_runners = list()
            if self.playing_colors:
                self.team_scores = dict(zip(self.playing_colors,
                                            [0] * len(self.playing_colors)))
            else:
                self.team_scores = dict()

    @requires_session
    def clean_up(self, session=None):
        """Cleans up after a round.

        :param session: a database session
        :type session: SQLAlchemy Session

        """
        zdslog.debug('Cleaning up')
        now = datetime.now()
        if not self.round_id:
            zdslog.debug("self.round_id: [%s]" % (self.round_id))
            return
        round = session.query(Round).get(self.round_id)
        if not self.stats_enabled or (not self.save_empty_rounds and \
                                      not len(round.aliases)):
            session.delete(round)
        else:
            zdslog.debug("Setting round end_time to [%s]" % (now))
            round.end_time = now
            s = "Adding %s to %s"
            ###
            # for p in self.players:
            #     a = get_alias(p.name, p.ip, round=round, session=session)
            #     if round not in a.rounds:
            #         zdslog.debug(s % (round, a))
            #         a.rounds.append(round)
            ###
            zdslog.debug("Updating %s" % (round))
            session.merge(round)
            for flag_touch in round.flag_touches:
                ###
                # Players can hold flags until a round ends, thus the
                # FlagTouch will never have a loss_time.  Technically,
                # however, the loss_time would be at the end of a round,
                # because you can't hold a flag when there is no round.
                ###
                ds = "Checking that %s has a loss_time"
                zdslog.debug(ds % (flag_touch))
                if not flag_touch.loss_time:
                    flag_touch.loss_time = now
                    zdslog.debug("Updating %s" % (flag_touch))
                    session.merge(flag_touch)
        self.round_id = None
        self.clear_state()

    @property
    def has_teams(self):
        return self.game_mode in TEAM_MODES

    @requires_session
    def get_round(self, session=None):
        """Gets this ZServ's current Round.

        :param session: a database session
        :type session: SQLAlchemy Session
        :rtype: :class:`~ZDStack.ZDSModels.Round`
        :returns: the current Round or None

        """
        zdslog.debug('Getting round')
        if self.round_id:
            round = session.query(Round).get(self.round_id)
            zdslog.debug("Returning %s from [%s]" % (round, self.round_id))
            return round
        else:
            es = "[%s]: No round associated with round_id [%s]"
            zdslog.error(es % (self.name, self.round_id))

    @requires_session
    def get_map(self, session=None):
        """Gets this ZServ's current Map.

        :param session: a database session
        :type session: SQLAlchemy Session
        :rtype: :class:`~ZDStack.ZDSModels.Map`
        :returns: the current Map or None

        """
        zdslog.debug('Getting map, session: %s' % (session))
        if self.map_number and self.map_name:
            zdslog.debug('Should be able to return a map')
            q = session.query(Map)
            q = q.filter_by(name=self.map_name, number=self.map_number)
            try:
                m = q.one()
                zdslog.debug('Returning %s 1' % (m))
            except NoResultFound:
                m = Map()
                m.name = self.map_name
                m.number = self.map_number
                session.add(m)
                zdslog.debug('Returning %s 2' % (m))
            return m

    @requires_session
    def get_game_mode(self, session=None):
        """Gets this ZServ's current GameMode.

        :param session: a database session
        :type session: SQLAlchemy Session
        :rtype: :class:`~ZDStack.ZDSModels.GameMode`
        :returns: the current GameMode

        """
        zdslog.debug('Getting game mode')
        try:
            q = session.query(GameMode)
            q = q.filter_by(name=self.game_mode, has_teams=self.has_teams)
            gm = q.one()
            zdslog.debug('Returning %s 1' % (gm))
        except NoResultFound:
            gm = GameMode()
            gm.name = self.game_mode
            gm.has_teams = self.has_teams
            session.add(gm)
            zdslog.debug('Returning %s 2' % (gm))
        return gm

    @requires_session
    def get_source_port(self, session=None):
        """Gets this ZServ's current (source) Port.

        :param session: a database session
        :type session: SQLAlchemy Session
        :rtype: :class:`~ZDStack.ZDSModels.Port`
        :returns: the current (source) Port

        """
        zdslog.debug('Getting source port')
        try:
            q = session.query(Port).filter_by(name=self.source_port)
            p = q.one()
        except NoResultFound:
            p = Port()
            p.name = self.source_port
            session.add(p)
        return p

    @requires_session
    def change_map(self, map_number, map_name, session=None):
        """Handles a map change event.

        :param map_number: the number of the new map
        :type map_number: int
        :param map_name: the name of the new map
        :type map_name: string
        :param session: a database session
        :type session: SQLAlchemy Session

        """
        zdslog.debug('Change Map')
        ###
        # Because there are no player reconnections at the beginning of rounds
        # in 1.08.08, we need to prevent anything from accessing the list of
        # players until we sync it up.
        ###
        with self.players.lock:
            self.clean_up(session=session)
            self.map_number = map_number
            self.map_name = map_name
            zdslog.debug('Acquiring session')
            game_mode = self.get_game_mode(session=session)
            map = self.get_map(session=session)
            zdslog.debug('Getting now')
            now = datetime.now()
            zdslog.debug('Creating new round')
            r = Round()
            r.game_mode_name = game_mode.name
            r.game_mode = game_mode
            r.map_id = map.id
            r.map = map
            r.start_time = now
            zdslog.debug('Created new round %s, id: %s' % (r, r.id))
            session.add(r)
            session.flush()
            session.refresh(r)
            zdslog.debug('Persisted new round %s, id: %s' % (r, r.id))
            if r.id is None:
                zdslog.error("Round %s has no ID")
            self.round_id = r.id
            zdslog.debug('%s Round ID: [%s]' % (self.name, self.round_id))
            self.players.sync(acquire_lock=False, session=session,
                              check_bans=True)
            zdslog.debug('Done changing map')

    def load_config(self, reload=False):
        """Loads this ZServ's config.

        :param reload: whether or not the configuration is being
                       reloaded; if this is the first load, there are
                       some things (like creating FIFOs, etc.) we need
                       to do that we don't want to do if the internal
                       zserv is still running
        :type reload: boolean

        """
        with self.config_lock:
            # zdslog.debug('')
            self.config.process_config(reload=reload) # does tons of ugly stuff
            gm = self.get_game_mode()
            source_port = self.get_source_port()
            with global_session() as session:
                if gm not in source_port.game_modes:
                    source_port.game_modes.append(gm)
                    session.merge(source_port)
                # if source_port not in gm.ports:
                #     gm.ports.append(source_port)
                #     session.merge(gm)
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
        """Tests whether or not the internal zserv process is running.

        :returns: whether or not the internal zserv process is running
        :rtype: boolean
        
        """
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
                self.start_time = datetime.now()
                self.restarts.append(datetime.now())
                with open(self.config_file, 'w') as fobj:
                    fobj.write(self.config.get_config_data())
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
                                   stderr=DEVNULL, bufsize=0, close_fds=True,
                                   cwd=self.home_folder)
                # self.fifo = self.zserv.stdout.fileno()
                # zdslog.debug("%s: FIFO: %s" % (self.name, self.fifo))
                # self.send_to_zserv('players') # avoids CPU spinning

    def stop(self, check_if_running=True, signum=15):
        """Stops the zserv process.

        :param check_if_running: whether or not to check if the
                                 internal zserv process is running
        :type check_if_running: boolean
        :param signum: the signal number to send to the zserv process,
                       15 (SIGTERM) by default
        :type signum: int
        :rtype: boolean or string
        :returns: if an error occurred while stopping the internal
                  zserv, it is returned as a string - otherwise False
                  is returned

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
                    self.start_time = None
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

        :param signum: the signal to send to the internal zserv,
                       SIGTERM by default
        :type signum: int

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

        :param message: the message to send (cannot contain newlines)
        :type message: string
        :param event_response_type: the type of event to wait for in
                                    response
        :type event_response_type: string
        :rtype: list of :class:`~ZDStack.LogEvent.LogEvent` instances
        :returns: a list of response events, if event_response_type is
                  None, the list will be empty

        """
        # zdslog.debug('')
        if '\n' in message or '\r' in message:
            es = "Message cannot contain newlines or carriage returns"
            raise ValueError(es)
        if not self.is_running():
            zdslog.error("Cannot send data to a stopped ZServ")
            return
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
            #                                                                #
            # Everything past this point only happens if event_response_type #
            # is not None and events are enabled.                            #
            #                                                                #
            zdslog.debug("Setting response type")
            self.response_events = []
            self.event_type_to_watch_for = event_response_type
            self.response_finished.clear()
            _send(message)
            response = []
            zdslog.debug("Waiting for response")
            ###
            # In case a server is restarted before a non-response event occurs,
            # we need a timeout here.  500ms is probably enough.
            ###
            self.response_finished.wait(.5)
            ###
            # We want to process this response before any other events, so make
            # other threads wait until we're finished processing the response.
            ###
            zdslog.debug("Response is finished")
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

###
# Commands:
#    acl_add
#    acl_clear
#    acl_remove
#    add_cvaroverride
#  * addban
#  * addbot
#  * addmap
#    addtempban
#    alias
#    archivecvar
#    atexit
#    banlist
#  * clearmaplist
#    cmdlist
#    corpsebot
#    countdecals
#    cvarlist
#    dumpclasses
#    dumpmapthings
#    dumpheap
#    dumpspawnables
#    echo
#    error
#    eval
#    exec
#    exit
#    gameversion
#  * get
#    key
#  * kick
#  * killban
#    list_cvaroverride
#    listbots
#  * map
#    mapskipby
#    mapskipto
#  * maplist
#    mem
#    pings
#    playerinfo
#  * players
#    playersounds
#    print
#    puke
#    pullin
#    quit
#  * removebots
#  * resetscores
#  * say
#    scriptstat
#  * set
#    setaltwads
#    skins
#    soundlinks
#    soundlist
#    spray
#  * toggle
#  * unset
#    voicepacks
#  * wads
###

    def zaddban(self, ip_address, reason='rofl'):
        """Adds a ban.

        :param ip_address: the IP address to ban
        :type ip_address: string
        :param reason: the reason for the ban
        :param type: string

        """
        # zdslog.debug('')
        return self.send_to_zserv('addban %s %s' % (ip_address, reason),
                                  'addban_command')

    def zaddtimedban(self, duration, ip_address, reason='rofl'):
        """Adds a ban with an expiration.

        :param duration: length of ban in minutes
        :type duration: int
        :param ip_address: the IP address to ban
        :type ip_address: string
        :param reason: the reason for the ban
        :param type: string

        """
        zdslog.debug("Adding timed ban for [%s]" % (ip_address))
        out = self.zaddban(ip_address, reason)
        args = [ip_address]
        t = Timer(duration * 60, self.remove_timed_ban, args)
        args.append(t)
        self.ban_timers.add(t)
        t.start()
        zdslog.debug("Ban Timers: %s" % (str(self.ban_timers)))
        return out

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
            out = self.zkillban(ip_address)
            self.ban_timers.remove(timer)
        return out

    def zaddbot(self, bot_name):
        """Adds a bot.

        :param bot_name: the name of the bot to add
        :type bot_name: string

        """
        # zdslog.debug('')
        return self.send_to_zserv('addbot %s' % (bot_name), 'addbot_command')

    def zaddmap(self, map_number):
        """Adds a map to the maplist.

        :param map_number: the number of the map to add
        :type map_number: int

        """
        # zdslog.debug('')
        return self.send_to_zserv('addmap %s' % (map_number))

    def zclearmaplist(self):
        """Clears the maplist."""
        # zdslog.debug('')
        return self.send_to_zserv('clearmaplist', 'clearmaplist_command')

    def zget(self, variable_name):
        """Gets a variable.

        :param variable_name: the name of the variable whose value is
                              to be returned
        :type variable_name: string
        :rtype: list of :class:`~ZDStack.LogEvent` instances

        """
        # zdslog.debug('')
        return self.send_to_zserv('get %s', 'get_command')

    def zkick(self, player_number, reason='rofl'):
        """Kicks a player.

        :param player_number: the number of the player to kick
        :type player_number: int
        :param reason: the reason for the kick
        :type reason: string

        """
        # zdslog.debug('')
        return self.send_to_zserv('kick %s %s' % (player_number, reason),
                                  'kick_command')

    def zkillban(self, ip_address):
        """Removes a ban.

        :param ip_address: the IP address to unban
        :type ip_address: string

        """
        # zdslog.debug('')
        return self.send_to_zserv('killban %s' % (ip_address),
                                  'killban_command')

    def zmap(self, map_number):
        """Changes the current map.

        :param map_number: the number of the map to change to
        :type map_number: int

        """
        # zdslog.debug('')
        return self.send_to_zserv('map %s' % (map_number))

    def zmaplist(self):
        """Gets the maplist.

        :rtype: list of :class:`~ZDStack.LogEvent` instances

        """
        # zdslog.debug('')
        return self.send_to_zserv('maplist', 'maplist_command')

    def zplayerinfo(self, player_number):
        """Returns information about a player.

        :param player_number: the number of the player for which to return
                              player information.
        :type player_number: string
        :rtype: list of :class:`~ZDStack.LogEvent` instances

        """
        return self.send_to_zserv('playerinfo %s' % (player_number),
                                  'playerinfo_command')

    def zplayers(self):
        """Returns a list of players in the server.
        
        :rtype: list of :class:`~ZDStack.LogEvent` instances
        
        """
        # zdslog.debug('')
        return self.send_to_zserv('players', 'players_command')

    def zremovebots(self):
        """Removes all bots."""
        # zdslog.debug('')
        return self.send_to_zserv('removebots', 'removebots_command')

    def zresetscores(self):
        """Resets all scores."""
        # zdslog.debug('')
        return self.send_to_zserv('resetscores', 'resetscores_command')

    def zsay(self, message):
        """Sends a message as '] CONSOLE ['.

        :param message: the message to send
        :type message: string

        """
        # zdslog.debug('')
        return self.send_to_zserv('say %s' % (message), 'say_command')

    def zset(self, variable_name, variable_value):
        """Sets a variable.

        :param variable_name: the name of the variable whose value is
                              to be set
        :type variable_name: string
        :param variable_value: the new valuable
        :type variable_value: string

        """
        # zdslog.debug('')
        s = 'set %s "%s"' % (variable_name, variable_value)
        return self.send_to_zserv(s, 'set_command')

    def ztoggle(self, boolean_variable):
        """Toggles a boolean variable.

        :param boolean_variable: the name of the variable whose value
                                 is to be toggled
        :type boolean_variable: string

        """
        # zdslog.debug('')
        return self.send_to_zserv('toggle %s' % (boolean_variable),
                                  'toggle_command')

    def zunset(self, variable_name):
        """Un-sets a variable.

        :param variable_name: the name of the variable whose value is
                              to be un-set
        :type variable_name: string

        """
        # zdslog.debug('')
        return self.send_to_zserv('unset %s' % (variable_name))

    def zwads(self):
        """Gets the currently used WADs.

        :rtype: list of :class:`~ZDStack.LogEvent` instances

        """
        # zdslog.debug('')
        return self.send_to_zserv('wads', 'wads_command')

