from __future__ import with_statement

import os
import time
import Queue
import select
import logging

from datetime import datetime, timedelta
from cStringIO import StringIO
from threading import Lock, Timer, Thread
from collections import deque

from ZDStack import ZDSThreadPool
from ZDStack import DIE_THREADS_DIE, MAX_TIMEOUT, TICK, PlayerNotFoundError, \
                    ZServNotFoundError, get_configfile, get_configparser, \
                    load_configparser, check_server_config_section, \
                    get_zdslog, get_zdaemon_banlist_data
from ZDStack.Utils import get_event_from_line, requires_instance_lock, \
                          parse_ban_line
from ZDStack.ZServ import ZServ
from ZDStack.Server import Server
from ZDStack.ZDSTask import Task
from ZDStack.ZDSRegexps import get_server_regexps
from ZDStack.ZDSAccessList import WhiteList, BanList, ZDaemonBanList
from ZDStack.ZDSConfigParser import ZDSConfigParser as CP
from ZDStack.ZDSConfigParser import RawZDSConfigParser as RCP
from ZDStack.ZDSEventHandler import ZServEventHandler

zdslog = get_zdslog()

class Stack(Server):

    """Stack is the main ZDStack class.
    
    .. attribute:: spawn_lock
        A Lock that must be acquired before a zserv can spawn.

    .. attribute:: szn_lock
        A Lock that must be acquired before modifying
        stopped_zserv_list.

    .. attribute:: zservs
        A dict mapping ZServ names to ZServ instances.

    .. attribute:: stopped_zserv_names
        A set of strings representing the names of stopped ZServ
        instances.

    .. attribute:: start_time
        A datetime representing the time the Stack started.

    .. attribute:: keep_checking_loglinks
        A boolean that, when set to False, does not reset the
        loglink_check_timer after checking log links.

    .. attribute:: keep_spawning_zservs
        A boolean that, when set to False, does not reset the
        zserv_check_timer after checking ZServs.

    .. attribute:: keep_polling
        A boolean that, when set to False, stops the ZServ Polling
        Thread.

    .. attribute:: keep_parsing
        A boolean that, when set to False, stops the ZServ Parsing
        Thread.

    .. attribute:: keep_handling_events
        A boolean that, when set to False, stops the Event Handling
        Thread.

    .. attribute:: regexps
        A list of :class:`~ZDStack.ZDSRegexps.Regexp` instances used to
        parse :class:`~ZDStack.ZServ` events.

    .. attribute:: event_handler
        A :class:`~ZDStack.ZDSEventHandler.ZServEventHandler` that
        handles :class:`~ZDStack.ZServ.ZServ` events.

    .. attribute:: output_queue
        A Queue where output lines are placed to be processed.

    .. attribute:: event_queue
        A Queue where events are placed to be processed.

    .. attribute:: loglink_check_timer
        A Timer that checks each :class:`~ZDStack.ZServ.ZServ`'s
        logfile links every 30 minutes.

    .. attribute:: zserv_check_timer
        A Timer that restarts each crashed ZServ every 500 milliseconds.

    .. attribute:: zdaemon_banlist_fetch_timer
        A Timer that fetches the ZDaemon master banlist ever 15 minutes.

    Stack does the following things:

      * Checks that all server log links and FIFOs exist every 30 min.
      * Checks that all ZServs are running every 500
        milliseconds
      * Polls all ZServs for output
      * Parses ZServ output lines into events
      * Passes events to the EventHandler and the ZServ's plugins
      * Handles incoming RPC requests

    """

    methods_requiring_authentication = []

    def __init__(self):
        """Initializes a Stack instance."""
        self.spawn_lock = Lock()
        self.szn_lock = Lock()
        # self.poller = select.poll()
        self.zservs = {}
        self.stopped_zserv_names = set()
        self.start_time = datetime.now()
        self.keep_checking_loglinks = False
        self.keep_spawning_zservs = False
        self.keep_fetching_zdaemon_banlist = False
        self.keep_polling = False
        self.keep_parsing = False
        self.keep_handling_events = False
        self.regexps = get_server_regexps()
        self.whitelist = WhiteList()
        self.banlist = BanList()
        self.zdaemon_banlist = ZDaemonBanList()
        Server.__init__(self)
        self.load_zservs()
        self.event_handler = ZServEventHandler()
        self.output_queue = Queue.Queue()
        self.event_queue = Queue.Queue()
        self.methods_requiring_authentication.append('start_zserv')
        self.methods_requiring_authentication.append('stop_zserv')
        self.methods_requiring_authentication.append('start_all_zservs')
        self.methods_requiring_authentication.append('stop_all_zservs')
        self.loglink_check_timer = None
        self.zserv_check_timer = None
        self.zdaemon_banlist_fetch_timer = None

    def start(self):
        """Starts this Stack."""
        # zdslog.debug('')
        self.keep_spawning_zservs = True
        self.keep_checking_loglinks = True
        self.keep_fetching_zdaemon_banlist = True
        self.keep_polling = True
        self.keep_parsing = True
        self.keep_handling_events = True
        if not self.loglink_check_timer:
            self.start_checking_loglinks()
        self.polling_thread = \
            ZDSThreadPool.get_thread(self.poll_zservs,
                                     "ZDStack Polling Thread",
                                     lambda: self.keep_polling == True)
        ZDSThreadPool.process_queue(self.output_queue, 'ZServ Output Queue',
                                    lambda: self.keep_parsing == True)
        ZDSThreadPool.process_queue(self.event_queue, 'ZServ Event Queue',
                            lambda: self.keep_handling_events == True)
        ###
        # Start the spawning timer last.
        ###
        if not self.zserv_check_timer:
            self.spawn_zservs()
        if not self.zdaemon_banlist_fetch_timer:
            self.fetch_zdaemon_banlist()
        Server.start(self)

    def stop(self):
        """Stops this Stack."""
        # zdslog.debug('')
        zdslog.debug("Cancelling check_timer")
        self.keep_checking_loglinks = False
        if self.loglink_check_timer:
            self.loglink_check_timer.cancel()
        self.keep_spawning_zservs = False
        if self.zserv_check_timer:
            self.zserv_check_timer.cancel()
        self.keep_fetching_zdaemon_banlist = False
        if self.zdaemon_banlist_fetch_timer:
            self.zdaemon_banlist_fetch_timer.cancel()
        zdslog.debug("Stopping all ZServs")
        self.stop_all_zservs()
        zdslog.debug("Stopping polling thread")
        self.keep_polling = False
        if self.polling_thread:
            zdslog.debug("Joining polling thread")
            ZDSThreadPool.join(self.polling_thread)
        zdslog.debug("Clearing output queue")
        self.keep_parsing = False
        self.output_queue.join()
        zdslog.debug("Clearing event queue")
        self.keep_handling_events = False
        self.event_queue.join()
        Server.stop(self)

    def start_checking_loglinks(self):
        """Starts checking every ZServ's log links every 30 minutes."""
        try:
            for zserv in self.zservs.values():
                try:
                    zserv.ensure_loglinks_exist()
                except Exception, e:
                    es = "Received error checking log links for [%s]: [%s]"
                    zdslog.error(es % (zserv.name, e))
                    continue
        finally:
            if self.keep_checking_loglinks:
                t = Timer(1800, self.start_checking_loglinks)
                self.loglink_check_timer = t
                self.loglink_check_timer.start()

    def spawn_zservs(self):
        """Spawns zservs, respawning if they've crashed."""
        now = datetime.now()
        with self.szn_lock:
            try:
                for zserv in self.zservs.values():
                    try:
                        if zserv.name in self.stopped_zserv_names or \
                           zserv.is_running():
                            ###
                            # The zserv is supposed to be stopped, or the zserv
                            # is already running, in either case we skip it.
                            ###
                            continue
                    ###
                    # This timer runs every 500ms.  So if the zserv has 2
                    # restarts in the last 4 seconds, stop trying to start it.
                    ###
                        if len(zserv.restarts) > 1:
                            second_most_recent_restart = zserv.restarts[-2]
                            diff = now - second_most_recent_restart
                            if diff <= timedelta(seconds=4):
                                es = "ZServ %s respawning too fast, stopping"
                                zdslog.error(es % (zserv.name))
                                zserv.stop(check_if_running=False)
                                self.stopped_zserv_names.add(zserv.name)
                                continue
                            else:
                                ###
                                # Don't want the restart list growing
                                # infinitely.
                                ###
                                zserv.restarts = zserv.restarts[-2:]
                        zserv.start()
                    except Exception, e:
                        es = "Received error while checking [%s]: [%s]"
                        zdslog.error(es % (zserv.name, e))
                        continue
            finally:
                if self.keep_spawning_zservs:
                    t = Timer(.5, self.spawn_zservs)
                    self.zserv_check_timer = t
                    self.zserv_check_timer.start()

    def fetch_zdaemon_banlist(self):
        """Fetches the ZDaemon banlist for servers who have it copied."""
        try:
            bans = []
            for x in get_zdaemon_banlist_data().splitlines():
                x = x.strip()
                if not x or x.startswith(';') or not x[0].isdigit():
                    continue
                bans.append(parse_ban_line(x))
            with self.zdaemon_banlist.lock:
                self.zdaemon_banlist.clear(acquire_lock=False)
                for ban in bans:
                    self.zdaemon_banlist.add_global(str(ban), ban.reason,
                                                    acquire_lock=False)
        finally:
            if self.keep_fetching_zdaemon_banlist:
                t = Timer(1800, self.fetch_zdaemon_banlist)
                self.zdaemon_banlist_fetch_timer = t
                self.zdaemon_banlist_fetch_timer.start()

    def poll_zservs(self):
        """Polls all ZServs for output."""
        ###
        # Rather than have a separate polling thread for each ZServ, I put
        # a big 'select' here for every (running) ZServ.  I know that 'poll'
        # scales better than 'select', but 'select' is easier to use and I
        # don't think anyone will ever run enough ZServs to notice.
        #
        # Also the select call gives up every second, which allows it to check
        # whether or not it should keep polling.
        ###
        stuff = [(z, z.fifo) for z in self.zservs.values() if z.fifo]
        if not stuff:
            time.sleep(TICK)
            return
        try:
            r, w, x = select.select([f for z, f in stuff], [], [], MAX_TIMEOUT)
        except select.error, e:
            errno, message = e.args
            if errno == 9:
                ###
                # Error code 9: Bad file descriptor: probably meaning FD was
                # closed.  We just want to try the whole thing again in this
                # case.
                ###
                return
            raise
        except TypeError:
            ###
            # This probably shouldn't happen, but if the ZServ's .fifo
            # attribute is None and it slips through somehow, the select()
            # call will try to call its .fileno() method, which will obviously
            # fail.  We just want to try the whole thing again in this case.
            ###
            return
        if not r:
            return
        readable = [(z, f) for z, f in stuff if f in r]
        for zserv, fd in readable:
            while 1:
                try:
                    ###
                    # I guess 1024 bytes should be a big enough chunk.
                    ###
                    data = os.read(fd, 1024)
                    if data:
                        logging.getLogger(zserv.name).info(data)
                        ds = "Got data from %r: [%r]"
                        zdslog.debug(ds % (zserv.name, data))
                        lines = data.splitlines()
                        if zserv._fragment:
                            lines[0] = zserv._fragment + lines[0]
                            zserv._fragment = None
                        if not data.endswith('\n'):
                            lines, zserv._fragment = lines[:-1], lines[-1]
                        output = (zserv, datetime.now(), lines)
                        task = Task(self.parse_zserv_output, args=output,
                                    name='Parsing')
                        self.output_queue.put_nowait(task)
                    else:
                        ###
                        # Non-blocking FDs should raise exceptions instead
                        # of returning nothing, but just for the hell of
                        # it.
                        ###
                        break
                except OSError, e:
                    if e.errno in (9, 11):
                        ###
                        # Error code 9 is described above.
                        #
                        # Error code 11: FD would have blocked... meaning
                        # we're at the end of the data stream.
                        ###
                        break
                    else:
                        ###
                        # We want other stuff to bubble up.
                        ###
                        raise

    def parse_zserv_output(self, zserv, dt, lines):
        """Parses ZServ output into events, places them in the event queue.
        
        :param zserv: the output's originating
                      :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :param dt: the time when the lines were generated
        :type dt: datetime
        :param lines: the output lines
        :type lines: list of strings
        
        """
        # zdslog.debug("Events for [%s]: %s" % (zserv.name, events))
        if not zserv.events_enabled:
            ###
            # If events are disabled, this is as far as we go.
            ###
            return
        for line in lines:
            try:
                event = get_event_from_line(line, self.regexps, dt)
            except Exception, e:
                es = "Received error processing line [%s] from [%s]: [%s]"
                zdslog.error(es % (line, zserv.name, e))
                continue
            if not event:
                ###
                # Skip junk events.
                #
                # Normally lines with no matching Regexp are converted as
                # 'junk' events.  In the modern age, however, we just don't
                # generate anything.  Here's what the mythical 'junk' event
                # used to look like:
                #
                #   return LogEvent(now, 'junk', d, 'junk', line))
                #
                # We do, on the other hand, want to let the ZServ know that its
                # response is finished, if it's waiting on something.
                #
                ###
                zdslog.debug("No event for [%s]" % (line))
                if zserv.event_type_to_watch_for:
                    zdslog.debug("Response is finished")
                    ###
                    # Received an event that was not a response to the
                    # command after events that were responses to the
                    # command, so notify the zserv that its response
                    # is complete.
                    ###
                    zserv.response_finished.set()
                    ###
                    # We want to wait until the ZServ finished processing
                    # the response, because the current event may depend
                    # upon it.
                    ###
                    zdslog.debug("Waiting until response is processed")
                    zserv.finished_processing_response.wait()
                    zdslog.debug("Done waiting")
                continue
            try:
                if event.type == 'message':
                    zdslog.debug("Converting message event")
                    ppn = event.data['possible_player_names']
                    c = event.data['contents'] 
                    player = zserv.players.get_first_matching_player(ppn)
                    if not player:
                        s = "Received a message from a non-existent player"
                        s += ", PPN: %s, Message: %s"
                        zdslog.error(s % (ppn, line))
                        event.category, event.type = ('junk', 'junk')
                    else:
                        zdslog.debug("Updating event.data")
                        m = c.replace(player.name, '', 1)[3:]
                        event.data = {'message': m, 'messenger': player}
                        zdslog.debug("Event data: %s" % (str(event.data)))
                if zserv.event_type_to_watch_for:
                    s = "%s is watching for %s events"
                    zdslog.debug(s % (zserv.name,
                                       zserv.event_type_to_watch_for))
                    if event.type == zserv.event_type_to_watch_for:
                        zdslog.debug("Found a response event")
                        zserv.response_events.append(event)
                    elif zserv.response_events:
                        zdslog.debug("Response is finished")
                        zserv.response_finished.set()
                        zdslog.debug("Waiting until response is processed")
                        zserv.finished_processing_response.wait()
                        zdslog.debug("Done waiting")
                    else:
                        zdslog.debug("Response hasn't started yet")
                task = Task(self.handle_events, args=[event, zserv],
                            name='%s Event Handling' % (event.type.capitalize()))
                s = "Putting [%s] from %s in the event queue"
                zdslog.debug(s % (event, zserv.name))
                ###
                # Because response events are saved by the ZServ, we don't need
                # a separate queue for them; whatever called send_to_zserv()
                # will process the events asynchronously.
                ###
                self.event_queue.put_nowait(task)
            except Exception, e:
                es = "Received error while processing event from [%s]: "
                es += "[%s]"
                zdslog.error(es % (zserv.name, e))
                continue

    def handle_events(self, event, zserv):
        """Handles events.

        :param event: the event to handle
        :type event: :class:`~ZDStack.LogEvent`
        :param zserv: the :class:`~ZDStack.ZServ.ZServ` instance that
                      generated the event.
        :type zserv: :class:`~ZDStack.ZServ.ZServ`

        """
        ds = "Handling %s event (Line: [%s])"
        zdslog.debug(ds % (event.type, event.line))
        handler = self.event_handler.get_handler(event.category)
        # zdslog.debug("Acquiring %s's event lock" % (zserv.name))
        with zserv.event_lock:
            # zdslog.debug("Acquired %s's event lock" % (zserv.name))
            handler(event, zserv)
            if zserv.plugins_enabled:
                for plugin in zserv.plugins:
                    ds = "Processing %s with %s"
                    zdslog.debug(ds % (event, plugin.__name__))
                    try:
                        plugin(event, zserv)
                    except Exception, e:
                        es = "Exception in plugin %s: [%s]"
                        zdslog.error(es % (plugin.__name__, e))
                        continue
        zdslog.debug("Finished handling %s event" % (event.type))

    def get_running_zservs(self):
        """Returns a list of ZServs whose internal zserv is running."""
        return [x for x in self.zservs.values() if x.is_running()]

    def get_stopped_zservs(self):
        """Returns a list of ZServs whose internal zserv isn't running."""
        return [x for x in self.zservs.values() if not x.is_running()]

    def check_all_zserv_configs(self, configparser):
        """Ensures that all ZServ configuration sections are correct.
        
        :param configparser: the configuration to check
        :type configparser: :class:`~ZDStack.ZDSConfigParser`

        If a configuration error is found, an Exception is raised.
        
        """
        # zdslog.debug('')
        for zserv in self.get_running_zservs():
            if not zserv.name in configparser.sections():
                es = "Cannot remove running zserv [%s] from the config."
                raise Exception(es % (zserv.name))

    def load_zservs(self):
        """Instantiates all configured ZServs."""
        zdslog.debug('Loading ZServs: %s' % (str(self.config.sections())))
        for zserv_name in self.config.sections():
            if zserv_name in self.zservs:
                zdslog.info("Reloading Config for [%s]" % (zserv_name))
                self.zservs[zserv_name].load_config(reload=True)
            else:
                zdslog.debug("Adding zserv [%s]" % (zserv_name))
                self.zservs[zserv_name] = ZServ(zserv_name, self)

    def load_config(self, config, reload=False):
        """Loads the configuration.

        :param config: the configuration to load
        :type config: :class:`~ZDStack.ZDSConfigParser.ZDSConfigParser`
        :param reload: whether or not the config is being reloaded
        :type reload: boolean

        """
        zdslog.debug('')
        raw_config = RCP(self.config_file)
        for section in raw_config.sections():
            raw_config.set(section, 'name', section)
        self.check_all_zserv_configs(config)
        Server.load_config(self, config, reload)
        self.raw_config = raw_config
        ###
        # accesslist_file = self.config.getpath('DEFAULT',
        #                                       'zdstack_global_accesslist_file')
        # new_access_list = AccessList(filename=accesslist_file)
        # if self.access_list:
        #     with self.access_list.lock:
        #         self.access_list.clear(acquire_lock=False)
        #         for s in new_access_list.sections():
        #             self.access_list.add_section(s, acquire_lock=False)
        #             for k, v in new_access_list.items(s):
        #                 self.access_list.set(s, k, v, acquire_lock=False)
        # else:
        #     self.access_list = new_access_list
        ###
        if reload:
            self.load_zservs()

    def start_zserv(self, zserv_name):
        """Starts a ZServ.

        :param zserv_name: the name of the ZServ to start
        :type zserv_name: string

        """
        # zdslog.debug('')
        zdslog.debug("Starting %s" % (zserv_name))
        if zserv_name not in self.zservs:
            raise ZServNotFoundError(zserv_name)
        if self.zservs[zserv_name].is_running():
            raise Exception("ZServ [%s] is already running" % (zserv_name))
        with self.szn_lock:
            self.zservs[zserv_name].start()
            try:
                self.stopped_zserv_names.remove(zserv_name)
            except KeyError:
                ###
                # zserv_name wasn't in self.stopped_zserv_names.
                ###
                pass
        zdslog.debug("Done starting %s" % (zserv_name))

    def stop_zserv(self, zserv_name):
        """Stops a ZServ.

        :param zserv_name: the name of the ZServ to start
        :type zserv_name: string

        """
        # zdslog.debug('')
        zdslog.debug("Stopping %s" % (zserv_name))
        if zserv_name not in self.zservs:
            raise ZServNotFoundError(zserv_name)
        if not self.zservs[zserv_name].is_running():
            raise Exception("ZServ [%s] is not running" % (zserv_name))
        with self.szn_lock:
            self.zservs[zserv_name].stop()
            self.stopped_zserv_names.add(zserv_name)
        zdslog.debug("Done stopping %s" % (zserv_name))

    def restart_zserv(self, zserv_name):
        """Restarts a ZServ.

        :param zserv_name: the name of the ZServ to start
        :type zserv_name: string

        """
        # zdslog.debug('')
        zdslog.debug("Restarting %s" % (zserv_name))
        self.stop_zserv(zserv_name)
        time.sleep(1)
        self.start_zserv(zserv_name)
        zdslog.debug("Done restarting %s" % (zserv_name))

    def start_all_zservs(self, names=None):
        """Starts all ZServs.

        :param names: an optional list of zserv_names which are to
                      be started - used as a limit
        :type names: list of strings

        """
        # zdslog.debug('')
        for zserv in self.get_stopped_zservs():
            if not names or zserv.name in names:
                self.start_zserv(zserv.name)

    def stop_all_zservs(self, names=None):
        """Stops all ZServs.

        :param names: an optional list of zserv_names which are to
                      be stopped - used as a limit
        :type names: list of strings

        """
        # zdslog.debug('')
        for zserv in self.get_running_zservs():
            if not names or zserv.name in names:
                try:
                    self.stop_zserv(zserv.name)
                except Exception, e:
                    if not str(e).endswith('is not running'):
                        ###
                        # We still want to stop the other servers.
                        ###
                        continue

    def restart_all_zservs(self, names=None):
        """Restarts all ZServs.

        :param names: an optional list of zserv_names which are to
                      be stopped - used as a limit
        :type names: list of strings

        """
        # zdslog.debug('')
        for zserv in self.get_running_zservs():
            if not names or zserv.name in names:
                self.restart_zserv(zserv.name)

    def get_zserv(self, zserv_name):
        """Returns a ZServ instance.
        
        :param zserv_name: the name of the ZServ to start
        :type zserv_name: string
        
        """
        # zdslog.debug('')
        if zserv_name not in self.zservs:
            raise ZServNotFoundError(zserv_name)
        return self.zservs[zserv_name]

    def list_zserv_names(self, names):
        """Returns a list of ZServ names.

        :param names: an optional list of zserv_names which are to
                      be returned - used as a limit
        :type names: list of strings

        """
        # zdslog.debug('')
        if names:
            return [x for x in self.zservs.keys() if x in names]
        else:
            return self.zservs.keys()

    def _get_zserv_info(self, zserv):
        """Returns a dict of zserv info.

        :param zserv: the :class:`~ZDStack.ZServ.ZServ` to get info for
        :type zserv: :class:`~ZDStack.ZServ.ZServ
        :rtype: dict

        """
        players = len([x for x in zserv.players if not x.disconnected])
        if hasattr(zserv, 'ip'):
            ip_address = zserv.ip
        else:
            ip_address = self.hostname
        if hasattr(zserv, 'max_players'):
            max_players = zserv.max_players
        else:
            max_players = 16
        return {'name': zserv.name,
                'hostname': zserv.hostname,
                'mode': zserv.game_mode,
                'wads': zserv.wads,
                'optional_wads': zserv.optional_wads,
                'ip': ip_address,
                'port': zserv.port,
                'players': players,
                'max_players': max_players,
                'map_name': zserv.map_name,
                'map_number': zserv.map_number,
                'round_id': zserv.round_id,
                'is_running': zserv.is_running()}

    def get_zserv_info(self, zserv_name):
        """Returns a dict of zserv info.

        :param zserv_name: the name of the ZServ to get info for
        :type zserv_name: string
        :rtype: dict
        :returns: {'name': <string: internal name of ZServ>,
                   'hostname': <string: hostname of ZServ>,
                   'mode': <string: Game mode of ZServ>,
                   'wads': <strings: list of ZServ's WADs>,
                   'optional_wads': <strings: list of ZServ's optional WADs>,
                   'ip': <string: the ZServ's IP address>,
                   'port': <int: ZServ's port>,
                   'players': <int: number of connected players>,
                   'max_players': <int: maximum number of connected players>,
                   'map_name': <string: name of the current map>,
                   'map_number': <int: number of the current map>,
                   'round_id': <int: ID of the current round>,
                   'is_running': <boolean: whether ZServ is currently running>}

        """
        return self._get_zserv_info(self.get_zserv(zserv_name))

    def get_all_zserv_info(self, names=None):
        """Returns a list of zserv info dicts.

        :param names: an optional list of zserv_names for which to
                      return information - used as a limit.
        :type names: list of strings

        See get_zserv_info() for more information.

        """
        if names:
            x = [y for y in self.zservs if y in names]
        else:
            x = [y for y in self.zservs]
        return [self.get_zserv_info(y) for y in x]

    def _items_to_section(self, name, items):
        """Converts a list of items into a ConfigParser section.

        :param name: the name of the section to generate
        :type name: string
        :param items: options and values
        :type: list of 2-tuples ('option', 'value')
        :rtype: string

        :returns: string representation of a configparser section, with
                  global and game-mode specific options stripped out

        """
        new_items = []
        for option, value in items:
            if not option.startswith('zdstack') and \
               not option.startswith('zdsweb') and \
               not option.startswith('ctf') and \
               not option.startswith('ffa') and \
               not option.startswith('teamdm') and \
               not option.startswith('coop') and \
               not option.startswith('duel') and \
               not option == 'root_folder':
                new_items.append((option, value))
        new_items.sort()
        return '[%s]\n' % (name) + '\n'.join(["%s: %s" % x for x in new_items])

    def get_zserv_config(self, zserv_name):
        """Returns a ZServ's configuration as a string.

        :param zserv_name: the zserv's name
        :type zserv_name: string

        """
        # zdslog.debug('')
        self.get_zserv(zserv_name)
        return self._items_to_section(zserv_name,
                                      self.raw_config.items(zserv_name))

    def set_zserv_config(self, zserv_name, data):
        """Sets a ZServ's config.

        :param zserv_name: the zserv's name
        :type zserv_name: string
        :param data: the new configuration data
        :type data: string

        """
        # zdslog.debug('')
        cp = RCP(StringIO(data), dummy=True)
        current_main_cp = load_configparser()
        for o, v in cp.items(zserv_name):
            current_main_cp.set(zserv_name, o, v)
        check_server_config_section(zserv_name, current_main_cp)
        main_cp = get_configparser()
        with main_cp.lock:
            for o, v in cp.items(zserv_name):
                if o != 'name':
                    main_cp.set(zserv_name, o, v, acquire_lock=False)
            main_cp.save(acquire_lock=False)
        self.config = get_configparser(reload=True)
        self.raw_config = RCP(self.config_file)
        for section in self.raw_config.sections():
            self.raw_config.set(section, 'name', section)
        self.get_zserv(zserv_name).load_config(reload=True)

    def send_to_zserv(self, zserv_name, message):
        """Sends a command to a running zserv process.

        :param zserv_name: the name of the ZServ to send the message to
        :type zserv_name: string
        :param message: the message to send
        :type message: string

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).send_to_zserv(message)

    def addban(self, zserv_name, ip_address, reason='rofl'):
        """Adds an address to a ZServ's banlist.

        :param zserv_name: the name of the ZServ to which the ban
                           should be added
        :type zserv_name: string
        :param ip_address: the IP address to ban
        :type ip_address: string
        :param reason: the reason for the ban
        :type reason: string

        """
        # zdslog.debug('')
        return self.banlist.add(self.get_zserv(zserv_name), ip_address, reason)

    ###
    # A couple aliases, because the ZDaemon server commands are not formatted
    # according to the convention within ZDStack, and because killban is
    # completely unintuitive... bans aren't alive... /me rolls eyes.
    ###

    def add_ban(self, zserv_name, ip_address, reason='rofl'):
        """Alias for :func:addban."""
        return self.addban(zserv_name, ip_address, reason)
    
    def remove_ban(self, zserv_name, ip_address):
        """Alias for :func:killban."""
        return self.killban(zserv_name, ip_address)

    def delete_ban(self, zserv_name, ip_address):
        """Alias for :func:killban."""
        return self.killban(zserv_name, ip_address)

    def add_global_ban(self, ip_address, reason='rofl'):
        """Adds an address to the global banlist.

        :param ip_address: the IP address to ban
        :type ip_address: string
        :param reason: the reason for the ban
        :type reason: string

        """
        self.banlist.add_global(ip_address, reason)

    def remove_global_ban(self, ip_address):
        """Removes an address from the global banlist.

        :param ip_address: the IP address to ban
        :type ip_address: string

        """
        self.banlist.remove_global(ip_address)

    def add_whitelist(self, zserv_name, ip_address):
        """Adds an address to a ZServ's whitelist."

        :param zserv_name: the name of the ZServ to which the
                           whitelist should be added
        :type zserv_name: string
        :param ip_address: the IP address to whitelist
        :type ip_address: string

        """
        self.whitelist.add(self.get_zserv(zserv_name), ip_address)

    def remove_whitelist(self, zserv_name, ip_address):
        """Adds an address to a ZServ's whitelist."

        :param zserv_name: the name of the ZServ to which the
                           whitelist should be added
        :type zserv_name: string
        :param ip_address: the IP address to whitelist
        :type ip_address: string

        """
        self.whitelist.remove(self.get_zserv(zserv_name), ip_address)

    def delete_whitelist(self, zserv_name, ip_address):
        """Alias for :func:remove_whitelist."""
        self.remove_whitelist(zserv_name, ip_address)

    def add_global_whitelist(self, ip_address):
        """Adds an address to the global whitelist.

        :param ip_address: the IP address to whitelist
        :type ip_address: string

        """
        self.whitelist.add_global(ip_address)

    def remove_global_whitelist(self, ip_address):
        """Removes an address from the global whitelist.

        :param ip_address: the IP address to whitelist
        :type ip_address: string

        """
        self.whitelist.remove_global(ip_address)

    def addbot(self, zserv_name, bot_name=None):
        """Adds a bot.

        :param zserv_name: the name of the ZServ
        :type zserv_name: string
        :param bot_name: the name of the bot to add
        :type bot_name: string

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zaddbot(bot_name)

    def addmap(self, zserv_name, map_number):
        """Adds a map to the maplist.

        :param zserv_name: the name of the ZServ
        :type zserv_name: string
        :param map_number: the number of the map to add
        :type map_number: string

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zaddmap(map_number)

    def clearmaplist(self, zserv_name):
        """Clears the maplist.

        :param zserv_name: the name of the ZServ
        :type zserv_name: string

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zclearmaplist()

    def get(self, zserv_name, variable_name):
        """Gets the value of a variable.

        :param zserv_name: the name of the ZServ
        :type zserv_name: string
        :param variable_name: the name of the variable
        :type variable_name: string
        :rtype: string
        :returns: the value of the variable as a string

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zget(variable_name)

    def kick(self, zserv_name, player_number, reason='rofl'):
        """Kicks a player from the zserv.

        :param zserv_name: the name of the ZServ
        :type zserv_name: string
        :param player_number: the numer of the player to kick
        :type player_number: string
        :param reason: the reason for the kick
        :type reason: string

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zkick(player_number, reason)

    def killban(self, zserv_name, ip_address):
        """Removes an address from a ZServ's banlist.

        :param zserv_name: the name of the ZServ from which the ban
                           should be removed
        :type zserv_name: string
        :param ip_address: the ip address to remove
        :type ip_address: string

        """
        # zdslog.debug('')
        return self.banlist.remove(self.get_zserv(zserv_name), ip_address)

    def map(self, zserv_name, map_number):
        """Changes the current map.

        :param zserv_name: the name of the ZServ
        :type zserv_name: string
        :param map_number: the number of the map to change to
        :type map_number: string

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zmap(map_number)

    def maplist(self, zserv_name):
        """Returns the maplist.

        :param zserv_name: the name of the ZServ
        :type zserv_name: string

        Returns a list of strings representing the numbers of the maps
        in the maplist.

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zmaplist()

    def players(self, zserv_name):
        """Returns a list of players and their info.

        :param zserv_name: the name of the ZServ
        :type zserv_name: string
        :rtype: list of :class:`~LogEvent` instances
        :returns:
          Each :class:`~LogEvent` instance represents one line of the
          of the zserv's response.  The dict looks like:
          {'player_num': 0, 'player_name': 'superman',
           'player_ip': '127.0.0.1', 'player_port': 40667}

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zplayers()

    def removebots(self, zserv_name):
        """Removes all bots.

        :param zserv_name: the name of the ZServ
        :type zserv_name: string

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zremovebots()

    def resetscores(self, zserv_name):
        """Resets all scores.

        :param zserv_name: the name of the ZServ
        :type zserv_name: string

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zresetscores()

    def say(self, zserv_name, message):
        """Sends a message from "] CONSOLE [".

        :param zserv_name: the name of the ZServ
        :type zserv_name: string
        :param message: the message to send
        :type message: string

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zsay(message)

    def set(self, zserv_name, variable_name, variable_value):
        """Sets the value of a variable

        :param zserv_name: the name of the ZServ
        :type zserv_name: string
        :param variable_name: the name of the variable
        :type variable_name: string
        :param variable_value: the new value of the variable
        :type variable_value: string

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zset(variable_name, variable_value)

    def toggle(self, zserv_name, boolean_variable):
        """Toggles a boolean option.

        :param zserv_name: the name of the ZServ
        :type zserv_name: string
        :param boolean_variable: the name of the variable
        :type boolean_variable: string

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).ztoggle(boolean_variable)

    def unset(self, zserv_name, variable_name):
        """Unsets a variable (removes it).

        :param zserv_name: the name of the ZServ
        :type zserv_name: string
        :param variable_name: the name of the variable
        :type variable_name: string

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zunset(variable_name)

    def wads(self, zserv_name):
        """Returns a list of the used WADs.

        :param zserv_name: the name of the ZServ
        :type zserv_name: string
        :rtype: list of strings
        :returns: Each list member is the name of a used WAD.

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zwads()

    def register_functions(self):
        """Registers RPC functions."""
        # zdslog.debug('')
        Server.register_functions(self)
        ###
        # The following RPC methods are removed because stats will be handled
        # by a separate module, and configuration should be done solely with
        # the 'get_zserv_config' and 'set_zserv_config' methods.
        #
        # self.rpc_server.register_function(self.get_zserv)
        # self.rpc_server.register_function(self.get_all_zservs)
        # self.rpc_server.register_function(self.get_remembered_stats)
        # self.rpc_server.register_function(self.get_all_remembered_stats)
        # self.rpc_server.register_function(self.get_current_map)
        # self.rpc_server.register_function(self.get_team)
        # self.rpc_server.register_function(self.get_all_teams)
        # self.rpc_server.register_function(self.get_player)
        # self.rpc_server.register_function(self.get_all_players)
        # self.rpc_server.register_function(self.list_player_names)
        ###
        ###
        # General ZDStack management functions
        ###
        self.rpc_server.register_function(self.start,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.stop,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.restart,
                                          requires_authentication=True)
        ###
        # zserv process management functions
        ###
        self.rpc_server.register_function(self.start_zserv,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.stop_zserv,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.restart_zserv,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.start_all_zservs,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.stop_all_zservs,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.restart_all_zservs,
                                          requires_authentication=True)
        ###
        # Information functions
        ###
        self.rpc_server.register_function(self.list_zserv_names)
        self.rpc_server.register_function(self.get_zserv_info)
        self.rpc_server.register_function(self.get_all_zserv_info)
        self.rpc_server.register_function(self.get_zserv_config,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.set_zserv_config,
                                          requires_authentication=True)
        ###
        # Command functions
        ###
        self.rpc_server.register_function(self.send_to_zserv,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.add_ban,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.add_whitelist,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.addban,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.add_global_ban,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.remove_global_ban,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.add_global_whitelist,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.remove_global_whitelist,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.addbot,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.addmap,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.clearmaplist,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.delete_ban,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.delete_whitelist,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.get,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.kick,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.remove_ban,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.remove_whitelist,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.killban,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.map,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.maplist,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.players,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.removebots,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.resetscores,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.say,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.set,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.toggle,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.unset,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.wads,
                                          requires_authentication=True)

