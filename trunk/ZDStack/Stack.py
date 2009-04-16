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
from ZDStack import DIE_THREADS_DIE, MAX_TIMEOUT, ZServNotFoundError, \
                    get_configfile, get_configparser, get_zdslog
from ZDStack.Utils import get_event_from_line, requires_instance_lock
from ZDStack.ZServ import ZServ
from ZDStack.Server import Server
from ZDStack.ZDSTask import Task
from ZDStack.ZDSRegexps import get_server_regexps
from ZDStack.ZDSDatabase import persist
from ZDStack.ZDSConfigParser import RawZDSConfigParser as RCP
from ZDStack.ZDSEventHandler import ZServEventHandler

zdslog = get_zdslog()

class Stack(Server):

    methods_requiring_authentication = []

    """Stack represents the main ZDStack class."""

    def __init__(self, debugging=False, stopping=False):
        """Initializes a Stack instance.

        debugging:   a boolean, whether or not debugging is enabled.
                     False by default.
        stopping:    a boolean that indicates whether or not the Stack
                     was initialized just to shutdown a running
                     ZDStack.  False by defalut.

        """
        self.spawn_lock = Lock()
        self.szn_lock = Lock()
        # self.poller = select.poll()
        self.zservs = {}
        self.stopped_zserv_names = set()
        self.start_time = datetime.now()
        self.keep_checking_loglinks = False
        self.keep_spawning_zservs = False
        self.keep_polling = False
        self.keep_parsing = False
        self.keep_handling_command_events = False
        self.keep_handling_generic_events = False
        self.keep_handling_plugin_events = False
        self.keep_persisting = False
        self.regexps = get_server_regexps()
        Server.__init__(self)
        self.load_zservs()
        self.event_handler = ZServEventHandler()
        self.output_queue = Queue.Queue()
        self.plugin_events = Queue.Queue()
        self.generic_events = Queue.Queue()
        self.command_events = Queue.Queue()
        self.methods_requiring_authentication.append('start_zserv')
        self.methods_requiring_authentication.append('stop_zserv')
        self.methods_requiring_authentication.append('start_all_zservs')
        self.methods_requiring_authentication.append('stop_all_zservs')
        self.loglink_check_timer = None
        self.zserv_check_timer = None

    def start(self):
        """Starts this Stack."""
        # zdslog.debug('')
        self.keep_spawning_zservs = True
        self.keep_checking_loglinks = True
        self.keep_polling = True
        self.keep_parsing = True
        self.keep_handling_generic_events = True
        self.keep_handling_command_events = True
        self.keep_handling_plugin_events = True
        self.keep_persisting = True
        if not self.loglink_check_timer:
            self.start_checking_loglinks()
        self.polling_thread = \
            ZDSThreadPool.get_thread(self.poll_zservs,
                                     "ZDStack Polling Thread",
                                     lambda: self.keep_polling == True)
        ZDSThreadPool.process_queue(self.output_queue, 'ZServ Output Queue',
                                    lambda: self.keep_parsing == True)
        ZDSThreadPool.process_queue(self.command_events, 'ZServ Command Queue',
                            lambda: self.keep_handling_command_events == True)
        ZDSThreadPool.process_queue(self.generic_events, 'ZServ Generic Queue',
                            lambda: self.keep_handling_generic_events == True)
        ZDSThreadPool.process_queue(self.plugin_events, 'ZServ Plugin Queue',
                            lambda: self.keep_handling_plugin_events == True)
        ###
        # Start the spawning timer last.
        ###
        if not self.zserv_check_timer:
            self.spawn_zservs()
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
        zdslog.debug("Clearing command event queue")
        self.keep_handling_command_events = False
        self.command_events.join()
        zdslog.debug("Clearing generic event queue")
        self.keep_handling_generic_events = False
        self.generic_events.join()
        zdslog.debug("Clearing plugin event queue")
        self.keep_handling_plugin_events = False
        self.plugin_events.join()
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
        try:
            for zserv in self.zservs.values():
                try:
                    with self.szn_lock:
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
                        with self.szn_lock:
                            second_most_recent_restart = zserv.restarts[-2]
                            diff = now - second_most_recent_restart
                            if diff <= timedelta(seconds=4):
                                es = "ZServ %s respawning too fast, stopping"
                                zdslog.error(es % (zserv.name))
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

    def poll_zservs(self):
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
        r, w, x = select.select([f for z, f in stuff], [], [], MAX_TIMEOUT)
        readable = [(z, f) for z, f in stuff if f in r]
        # if readable:
        #     zdslog.debug("Readable: %s" % (str(readable)))
        for zserv, fd in readable:
            while 1:
                # zdslog.debug("Reading data from [%s]" % (zserv.name))
                try:
                    ###
                    # I guess 1024 bytes should be a big enough chunk.
                    ###
                    data = os.read(fd, 1024)
                    if data:
                        # zdslog.debug("Got %d bytes" % (len(data)))
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
                        # Non-blocking FDs should raise exceptions instead of
                        # returning nothing, but just for the hell of it.
                        ###
                        # zdslog.debug("No data")
                        break
                except OSError, e:
                    if e.errno == 11:
                        ###
                        # Error code 11: FD would have blocked... meaning
                        # we're at the end of the data stream.
                        ###
                        # zdslog.debug("FD would have blocked")
                        break
                    else:
                        ###
                        # We want other stuff to bubble up.
                        ###
                        # zdslog.debug("Raising exception")
                        raise

    def parse_zserv_output(self, zserv, dt, lines):
        """Parses ZServ output into events, places them in the event queue."""
        # zdslog.debug("Events for [%s]: %s" % (zserv.name, events))
        if zserv.save_logfile:
            logging.getLogger(zserv.name).info('\n'.join(lines))
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
                ###
                continue
            try:
                if event.type == 'message':
                    zdslog.debug("Converting message event")
                    ppn = event.data['possible_player_names']
                    c = event.data['contents'] 
                    if isinstance(ppn, basestring):
                        try:
                            player = zserv.players.get(name=ppn)
                        except PlayerNotFoundError:
                            s = "Received message from non-existent player [%s]"
                            zdslog.error(s % (ppn))
                    else:
                        player = zserv.players.get_first_matching_player(ppn)
                        if not player:
                            s = "Received a message from a non-existent player"
                            s += ", PPN: %s"
                            zdslog.error(s % (str(ppn)))
                        else:
                            m = c.replace(player.name, '', 1)[3:]
                            event.data = {'message': m, 'messenger': player}
                if zserv.event_type_to_watch_for:
                    s = "%s is watching for %s events"
                    zdslog.debug(s % (zserv.name,
                                       zserv.event_type_to_watch_for))
                    if event.type == zserv.event_type_to_watch_for:
                        zdslog.debug("Found a response event")
                        zserv.response_events.append(event)
                    elif zserv.response_events:
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
            except Exception, e:
                es = "Received error while processing event from [%s]: "
                es += "[%s]"
                zdslog.error(es % (zserv.name, e))
                continue
            s = "Put [%s] from %s in the %s queue"
            if event.category == 'command':
                queue_name = 'command'
                queue = self.command_events
            elif event.category != 'command':
                queue_name = 'generic'
                queue = self.generic_events
            else:
                raise Exception("What the hell")
            task = Task(self.handle_generic_events, args=[event, zserv],
                        name='%s Event Handling' % (event.type.capitalize()))
            queue.put_nowait(task)
            # zdslog.debug(s % (event, zserv.name, queue_name))
            if zserv.plugins_enabled:
                f = lambda: self.handle_plugin_events(event, zserv)
                t = Task(self.handle_plugin_events, args=[event, zserv],
                         name='%s Event Handling' % (event.type.capitalize()))
                # zdslog.debug(s % (event.type, zserv.name, 'plugin'))
                self.plugin_events.put_nowait(t)

    def handle_generic_events(self, event, zserv):
        """Handles generic events.

        event: a LogEvent instance.
        zserv: the ZServ instance that generated the event.

        """
        handler = self.event_handler.get_handler(event.category)
        if handler:
            s = "Handling %s event (Line: [%s])" % (event.type, event.line)
            zdslog.debug(s)
            ###
            # This should return a new model... or nothing.
            ###
            handler(event, zserv)
            zdslog.debug("Finished handling %s event" % (event.type))
        else:
            pass
            # zdslog.debug("No handler set for %s" % (event.type))

    def handle_plugin_events(self, event, zserv):
        """Handles plugin events.

        event: a LogEvent instance.
        zserv: the ZServ instance that generated the event.

        """
        zdslog.debug("Sending %s to %s's plugins" % (event, zserv.name))
        for plugin in zserv.plugins:
            zdslog.debug("Processing %s with %s" % (event, plugin.__name__))
            try:
                ###
                # If a plugin wants to persist something (God forbid), then
                # they'll have to do it themselves.
                ###
                plugin(event, zserv)
            except Exception, e:
                es = "Exception in plugin %s: [%s]"
                zdslog.error(es % (plugin.__name__, e))
                continue

    def get_running_zservs(self):
        """Returns a list of ZServs whose internal zserv is running."""
        return [x for x in self.zservs.values() if x.is_running()]

    def get_stopped_zservs(self):
        """Returns a list of ZServs whose internal zserv isn't running."""
        return [x for x in self.zservs.values() if not x.is_running()]

    def check_all_zserv_configs(self, configparser):
        """Ensures that all ZServ configuration sections are correct."""
        # zdslog.debug('')
        for zserv in self.get_running_zservs():
            if not zserv.name in configparser.sections():
                es = "Cannot remove running zserv [%s] from the config."
                raise Exception(es % (zserv_name))

    def load_zservs(self):
        """Instantiates all configured ZServs."""
        zdslog.debug('Loading ZServs: %s' % (str(self.config.sections())))
        for zserv_name in self.config.sections():
            if zserv_name in self.zservs:
                zdslog.info("Reloading Config for [%s]" % (zserv_name))
                self.zservs[zserv_name].reload_config()
            else:
                zdslog.debug("Adding zserv [%s]" % (zserv_name))
                self.zservs[zserv_name] = ZServ(zserv_name, self)

    def load_config(self, config, reload=False):
        """Loads the configuration.

        reload: a boolean, whether or not the configuration is being
                reloaded.

        """
        zdslog.debug('')
        raw_config = RCP(self.config_file)
        for section in raw_config.sections():
            raw_config.set(section, 'name', section)
        self.check_all_zserv_configs(config)
        Server.load_config(self, config, reload)
        self.raw_config = raw_config
        if reload:
            self.load_zservs()

    def start_zserv(self, zserv_name):
        """Starts a ZServ.

        zserv_name: a string representing the name of a ZServ to start

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

        zserv_name: a string representing the name of a ZServ to stop

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

        zserv_name: a string representing the name of a ZServ to
                    restart

        """
        # zdslog.debug('')
        zdslog.debug("Restarting %s" % (zserv_name))
        self.stop_zserv(zserv_name)
        time.sleep(1)
        self.start_zserv(zserv_name)
        zdslog.debug("Done restarting %s" % (zserv_name))

    def start_all_zservs(self):
        """Starts all ZServs."""
        # zdslog.debug('')
        for zserv in self.get_stopped_zservs():
            self.start_zserv(zserv.name)

    def stop_all_zservs(self, stop_logfiles=False):
        """Stops all ZServs.
        
        stop_logfiles: a boolean that, if True, stops the logfiles of
                       the ZServ as well.  False by default.
        
        """
        # zdslog.debug('')
        for zserv in self.get_running_zservs():
            try:
                self.stop_zserv(zserv.name)
            except Exception, e:
                if not str(e).endswith('is not running'):
                    ###
                    # We still want to stop the other servers.
                    ###
                    continue


    def restart_all_zservs(self):
        """Restars all ZServs."""
        # zdslog.debug('')
        for zserv in self.get_running_zservs():
            self.restart_zserv(zserv.name)

    def get_zserv(self, zserv_name):
        """Returns a ZServ instance.
        
        zserv_name: a string representing the name of the ZServ to
                    return
        
        """
        # zdslog.debug('')
        if zserv_name not in self.zservs:
            raise ZServNotFoundError(zserv_name)
        return self.zservs[zserv_name]

    def list_zserv_names(self):
        """Returns a list of ZServ names."""
        # zdslog.debug('')
        return self.zservs.keys()

    def _get_zserv_info(self, zserv):
        """Returns a dict of zserv info.

        zserv: a ZServ instance for which info is to be returned.

        The returned dict is formatted as follows:

          {'name': <string: internal name of ZServ>,
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
           'is_running': <boolean: whether ZServ is currently running>}

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
                'mode': zserv.raw_game_mode,
                'wads': zserv.wads,
                'optional_wads': zserv.optional_wads,
                'ip': ip_address,
                'port': zserv.port,
                'players': players,
                'max_players': max_players,
                'map_name': zserv.map.name,
                'map_number': zserv.map.number,
                'is_running': zserv.is_running()}

    def get_zserv_info(self, zserv_name):
        """Returns a dict of zserv info.

        zserv_name: a string representing the name of the ZServ for
                    which info is to be returned.

        See _get_zserv_info() for more information.

        """
        zserv = self.get_zserv(zserv_name)
        return self._get_zserv_info(self.get_zserv(zserv_name))

    def get_all_zserv_info(self):
        """Returns a list of zserv info dicts.

        See _get_zserv_info() for more information.

        """
        return [self._get_zserv_info(x) for x in self.zservs.values()]

    def _items_to_section(self, name, items):
        """Converts a list of items into a ConfigParser section.

        name:  a string representing the name of the section to
               generate.
        items: a list of option, value pairs (strings).

        This strips out the global and game-mode specific options.

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

        zserv_name: a string representing the ZServ's name

        """
        # zdslog.debug('')
        self.get_zserv(zserv_name)
        return self._items_to_section(zserv_name,
                                      self.raw_config.items(zserv_name))

    def set_zserv_config(self, zserv_name, data):
        """Sets a ZServ's config.

        zserv_name: a string representing the ZServ's name
        data:       a string representing the new configuration data

        """
        # zdslog.debug('')
        sio = StringIO(data)
        cp = RCP(sio, dummy=True)
        main_cp = get_configparser()
        with main_cp.lock:
            for o, v in cp.items(zserv_name):
                main_cp.set(zserv_name, o, v, acquire_lock=False)
            main_cp.save(acquire_lock=False)
        self.initialize_config(reload=True)
        self.get_zserv(zserv_name).reload_config()

    def send_to_zserv(self, zserv_name, message):
        """Sends a command to a running zserv process.

        zserv_name: a string representing the name of the ZServ to
                    send the message to
        message:    a string, the message to send

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).send_to_zserv(message)

    def addban(self, zserv_name, ip_address, reason='rofl'):
        """Adds a ban.

        zserv_name: a string representing the name of the ZServ to add
                    the ban to
        ip_address: a string representing the IP address to ban
        reason:     a string representing the reason for the ban

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zaddban(ip_address, reason)

    def addbot(self, zserv_name, bot_name=None):
        """Adds a bot.

        zserv_name: a string representing the name of the ZServ to add
                    the bot to
        bot_name:   a string representing the name of the bot to add

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zaddbot(bot_name)

    def addmap(self, zserv_name, map_number):
        """Adds a map to the maplist.

        zserv_name: a string representing the name of the ZServ to add
                    the map to
        map_number: a string representing the number of the map to add

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zaddmap(map_number)

    def clearmaplist(self, zserv_name):
        """Clears the maplist.

        zserv_name: a string representing the name of the ZServ whose
                    maplist is to be cleared

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zclearmaplist()

    def get(self, zserv_name, variable_name):
        """Gets the value of a variable.

        zserv_name:    a string representing the name of the ZServ to
                       retrieve the variable value from
        variable_name: a string representing the name of the variable
                       whose value is to be retrieved

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zget(variable_name)

    def kick(self, zserv_name, player_number, reason='rofl'):
        """Kicks a player from the zserv.

        zserv_name:    a string representing the name of the ZServ to
                       kick the player from
        player_number: a string representing the number of the player
                       to kick
        reason:        a string representing the reason for the kick

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zkick(player_number, reason)

    def killban(self, zserv_name, ip_address):
        """Removes a ban.

        zserv_name: a string representing the name of the ZServ to
                    remove the ban from
        ip_address: a string representing the IP address to remove the
                    ban for

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zkillban(ip_address)

    def map(self, zserv_name, map_number):
        """Changes the current map.

        zserv_name: a string representing the name of the ZServ to
                    change the map on
        map_number: a string representing the number of the map to
                    change to

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zmap(map_number)

    def maplist(self, zserv_name):
        """Returns the maplist.

        zserv_name: a string representing the name of the ZServ to
                    retrieve the maplist for

        Returns a list of strings representing the numbers of the maps
        in the maplist.

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zmaplist()

    def players(self, zserv_name):
        """Returns a list of players and their info.

        zserv_name: a string representing the name of the ZServ to
                    list the players for

        Returns a list of strings representing the number, name, and
        IP address of all players.

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zplayers()

    def removebots(self, zserv_name):
        """Removes all bots.

        zserv_name: a string representing the name of the ZServ to
                    remove the bots from

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zremovebots()

    def resetscores(self, zserv_name):
        """Resets all scores.

        zserv_name: a string representing the name of the ZServ to
                    reset the scores for

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zresetscores()

    def say(self, zserv_name, message):
        """Sends a message from "] CONSOLE [".

        zserv_name: a string representing the name of the ZServ to
                    send the message to
        message:    a string, the message to send

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zsay(message)

    def set(self, zserv_name, variable_name, variable_value):
        """Sets the value of a variable

        zserv_name:     a string representing the name of the ZServ
        variable_name:  a string representing the name of the variable
                        to set
        variable_value: a string representing the new value of the
                        variable

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zset(variable_name, variable_value)

    def toggle(self, zserv_name, boolean_variable):
        """Toggles a boolean option.

        zserv_name:       a string representing the name of the ZServ
        boolean_variable: a string representing the name of the
                          boolean variable to toggle on or off

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).ztoggle(boolean_variable)

    def unset(self, zserv_name, variable_name):
        """Unsets a variable (removes it).

        zserv_name:    a string representing the name of the ZServ to
                       remove the variable from
        variable_name: the name of the variable to unset

        """
        # zdslog.debug('')
        return self.get_zserv(zserv_name).zunset(variable_name)

    def wads(self, zserv_name):
        """Returns a list of the used WADs.

        zserv_name: a string representing the name of the ZServ to add
                    the bot to

        Returns a list of strings representing the names of the used
        WADs.

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
        # Process management functions
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
        self.rpc_server.register_function(self.addban,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.addbot,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.addmap,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.clearmaplist,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.get,
                                          requires_authentication=True)
        self.rpc_server.register_function(self.kick,
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

