import os
import time
import select
import logging

from datetime import datetime
from threading import Lock, Timer, Thread
from StringIO import StringIO

from ZDStack import ZDSThreadPool
from ZDStack import DIE_THREADS_DIE, MAX_TIMEOUT, ZServNotFoundError, \
                    get_configfile, get_configparser
from ZDStack.Utils import yes
from ZDStack.ZServ import ZServ
from ZDStack.Server import Server
from ZDStack.ZDSThreadPool import get_thread
from ZDStack.ZDSConfigParser import RawZDSConfigParser as RCP

class AuthenticationError(Exception):

    def __init__(self, username, method):
        es = "Error: Access to method [%s] was denied for user [%s]"
        Exception.__init__(self, es % (method, username))

class Stack(Server):

    methods_requiring_authentication = []

    """Stack represents the main ZDStack class."""

    ###
    # TODO: a lot of the zserv-related methods can be accessed via RPC, and
    #       none of the access to self.zservs is threadsafe, add lock!
    ###

    def __init__(self, debugging=False, stopping=False):
        """Initializes a Stack instance.

        debugging:   a boolean, whether or not debugging is enabled.
                     False by default.
        stopping:    a boolean that indicates whether or not the Stack
                     was initialized just to shutdown a running
                     ZDStack.  False by defalut.

        """
        self.spawn_lock = Lock()
        self.poller = select.poll()
        self.zservs = {}
        self.start_time = datetime.now()
        self.keep_polling = True
        self.polling_thread = None
        Server.__init__(self, debugging)
        self.methods_requiring_authentication.append('start_zserv')
        self.methods_requiring_authentication.append('stop_zserv')
        self.methods_requiring_authentication.append('start_all_zservs')
        self.methods_requiring_authentication.append('stop_all_zservs')
        self.loglink_check_timer = None
        if not stopping:
            self.start_checking_loglinks()

    def start_checking_loglinks(self):
        """Starts checking every ZServ's log links every 30 minutes."""
        try:
            for zserv in self.zservs.values():
                zserv.ensure_loglinks_exist()
        finally:
            self.loglink_check_timer = Timer(1800, self.start_checking_loglinks)
            self.loglink_check_timer.start()

    def get_running_zservs(self):
        """Returns a list of ZServs whose internal zserv is running."""
        return [x for x in self.zservs.values() if x.is_running()]

    def get_stopped_zservs(self):
        """Returns a list of ZServs whose internal zserv isn't running."""
        return [x for x in self.zservs.values() if not x.is_running()]

    def poll_zserv_output(self):
        ###
        # Rather than have a separate polling thread for each ZServ, I put
        # a big 'select' here for every (running) ZServ.  I know that 'poll'
        # scales better than 'select', but 'select' is easier to use and I
        # don't think anyone will ever run enough ZServs to notice.
        #
        # Also the select call gives up every second, which allows it to check
        # whether or not it should keep polling.
        ###
        stuff = [(z, z.fifo) for z in self.get_running_zservs()]
        r, w, x = select.select([f for z, f in stuff], [], [], MAX_TIMEOUT)
        readable = [(z, f) for z, f in stuff if f in r]
        # if readable:
        #     logging.debug("Readable: %s" % (str(readable)))
        for zserv, fd in readable:
            # logging.debug("Reading data from [%s]" % (zserv.name))
            data = ''
            while 1:
                try:
                    ###
                    # I guess 1024 bytes should be a big enough chunk.
                    ###
                    data += os.read(fd, 1024)
                except OSError, e:
                    if e.errno == 11:
                        ###
                        # Error code 11: FD would have blocked... meaning
                        # we're at the end of the data stream.
                        ###
                        break
                    else:
                        ###
                        # Something else happened, freak out.
                        ###
                        raise
                if data:
                    # logging.debug("Data from [%s]: [%s]" % (zserv.name, data))
                    zserv.logfile.write(data)
                else:
                    break

    def check_all_zserv_configs(self, config):
        """Ensures that all ZServ configuration sections are correct."""
        # logging.debug('')
        for zserv in self.get_running_zservs():
            if not zserv.name in sections:
                es = "Cannot remove running zserv [%s] from the config."
                raise Exception(es % (zserv_name))

    def load_zservs(self):
        """Instantiates all configured ZServs."""
        # logging.debug('')
        for zserv_name in self.config.sections():
            zs_config = dict(self.config.items(zserv_name))
            if zserv_name in self.zservs:
                logging.info("Reloading Config for [%s]" % (zserv_name))
                self.zservs[zserv_name].reload_config(zs_config)
            else:
                logging.debug("Adding zserv [%s]" % (zserv_name))
                self.zservs[zserv_name] = ZServ(zserv_name, zs_config, self)

    def load_config(self, config, reload=False):
        """Loads the configuration.

        reload: a boolean, whether or not the configuration is being
                reloaded.

        """
        # logging.debug('')
        raw_config = RCP(self.config_file, allow_duplicate_sections=False)
        for section in raw_config.sections():
            raw_config.set(section, 'name', section)
        self.check_all_zserv_configs(config)
        Server.load_config(self, config, reload)
        self.config = config
        self.raw_config = raw_config
        self.load_zservs()

    def start_zserv(self, zserv_name):
        """Starts a ZServ.

        zserv_name: a string representing the name of a ZServ to start

        """
        # logging.debug('')
        if zserv_name not in self.zservs:
            raise ZServNotFoundError(zserv_name)
        if self.zservs[zserv_name].is_running():
            raise Exception("ZServ [%s] is already running" % (zserv_name))
        self.zservs[zserv_name].start()

    def stop_zserv(self, zserv_name):
        """Stops a ZServ.

        zserv_name: a string representing the name of a ZServ to stop

        """
        # logging.debug('')
        if zserv_name not in self.zservs:
            raise ZServNotFoundError(zserv_name)
        if not self.zservs[zserv_name].is_running():
            raise Exception("ZServ [%s] is not running" % (zserv_name))
        self.zservs[zserv_name].stop()

    def restart_zserv(self, zserv_name):
        """Restarts a ZServ.

        zserv_name: a string representing the name of a ZServ to
                    restart

        """
        # logging.debug('')
        self.stop_zserv(zserv_name)
        time.sleep(1)
        self.start_zserv(zserv_name)

    def start_all_zservs(self):
        """Starts all ZServs."""
        # logging.debug('')
        for zserv in self.get_stopped_zservs():
            zserv.start()

    def stop_all_zservs(self, stop_logfiles=False):
        """Stops all ZServs.
        
        stop_logfiles: a boolean that, if True, stops the logfiles of
                       the ZServ as well.  False by default.
        
        """
        # logging.debug('')
        for zserv in self.get_running_zservs():
            zserv.stop(stop_logfile=stop_logfiles)

    def restart_all_zservs(self):
        """Restars all ZServs."""
        # logging.debug('')
        for zserv in self.get_running_zservs():
            zserv.restart()

    def start(self):
        """Starts this Stack."""
        # logging.debug('')
        self.keep_polling = True
        self.start_all_zservs()
        self.polling_thread = \
            ZDSThreadPool.get_thread(target=self.poll_zserv_output,
                                     name="ZDStack Polling Thread",
                                     keep_going=lambda: self.keep_polling)
        Server.start(self)

    def stop(self):
        """Stops this Stack."""
        # logging.debug('')
        logging.debug("Cancelling check_timer")
        if self.loglink_check_timer:
            self.loglink_check_timer.cancel()
        logging.debug("Stopping all ZServs")
        self.stop_all_zservs(stop_logfiles=False)
        logging.debug("Stopping all polling")
        self.keep_polling = False
        if self.polling_thread:
            logging.debug("Joining polling thread")
            ZDSThreadPool.join(self.polling_thread)
        for zserv in self.get_stopped_zservs():
            zserv.logfile.stop_listeners()
        Server.stop(self)

    def get_zserv(self, zserv_name):
        """Returns a ZServ instance.
        
        zserv_name: a string representing the name of the ZServ to
                    return
        
        """
        # logging.debug('')
        if zserv_name not in self.zservs:
            raise ZServNotFoundError(zserv_name)
        return self.zservs[zserv_name]

    def list_zserv_names(self):
        """Returns a list of ZServ names."""
        # logging.debug('')
        return self.zservs.keys()

    def _get_zserv_info(self, zserv):
        """Returns a dict of zserv info.

        zserv: a ZServ instance for which info is to be returned.

        """
        players = len([x for x in zserv.players if not x.disconnected])
        name, number = (zserv.map.name, zserv.map.number)
        running = zserv.is_running()
        return {'name': zserv.name, 'players': players, 'map_name': name,
                'map_number': number, 'is_running': running}

    def get_zserv_info(self, zserv_name):
        """Returns a dict of zserv info.

        zserv_name: a string representing the name of the ZServ for
                    which info is to be returned.

        The returned dict is formatted as follows:

        {'name': <internal name of zserv instance as string>,
         'players': <current number of players as int>,
         'map_name': <current name of map as string>,
         'map_number': <current number of map as int>,
         'is_running': <boolean whether or not ZServ is running>}

        """
        zserv = self.get_zserv(zserv_name)
        return self._get_zserv_info(self.get_zserv(zserv_name))

    def get_all_zserv_info(self):
        """Returns a list of zserv info dicts.

        See get_zserv_info() for more information.

        """
        return [self._get_zserv_info(x) for x in self.zservs.values()]

    def _items_to_section(self, name, items):
        """Converts a list of items into a ConfigParser section.

        name:  a string representing the name of the section to
               generate.
        items: a list of option, value pairs (strings).

        """
        return '[%s]\n' % (name) + '\n'.join(["%s: %s" % x for x in items])

    def get_zserv_config(self, zserv_name):
        """Returns a ZServ's configuration as a string.

        zserv_name: a string representing the ZServ's name

        """
        # logging.debug('')
        self.get_zserv(zserv_name)
        return self._items_to_section(zserv_name,
                                      self.raw_config.items(zserv_name))

    def set_zserv_config(self, zserv_name, data):
        """Sets a ZServ's config.

        zserv_name: a string representing the ZServ's name
        data:       a string representing the new configuration data

        """
        # logging.debug('')
        cp = RCP()
        sio = StringIO(data)
        cp.readfp(sio)
        main_cp = get_configparser()
        for o, v in cp.items(zserv_name):
            main_cp.set(zserv_name, o, v)
        main_cp.save()
        self.initialize_config(get_configfile(), reload=True)
        zs_config = dict(self.config.items(zserv_name))
        self.get_zserv(zserv_name).reload_config(zs_config)

    def send_to_zserv(self, zserv_name, message):
        """Sends a command to a running zserv process.

        zserv_name: a string representing the name of the ZServ to
                    send the message to
        message:    a string, the message to send

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).send_to_zserv(message)

    def addban(self, zserv_name, ip_address, reason='rofl'):
        """Adds a ban.

        zserv_name: a string representing the name of the ZServ to add
                    the ban to
        ip_address: a string representing the IP address to ban
        reason:     a string representing the reason for the ban

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zaddban(ip_address, reason)

    def addbot(self, zserv_name, bot_name=None):
        """Adds a bot.

        zserv_name: a string representing the name of the ZServ to add
                    the bot to
        bot_name:   a string representing the name of the bot to add

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zaddbot(bot_name)

    def addmap(self, zserv_name, map_number):
        """Adds a map to the maplist.

        zserv_name: a string representing the name of the ZServ to add
                    the map to
        map_number: a string representing the number of the map to add

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zaddmap(map_number)

    def clearmaplist(self, zserv_name):
        """Clears the maplist.

        zserv_name: a string representing the name of the ZServ whose
                    maplist is to be cleared

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zclearmaplist()

    def get(self, zserv_name, variable_name):
        """Gets the value of a variable.

        zserv_name:    a string representing the name of the ZServ to
                       retrieve the variable value from
        variable_name: a string representing the name of the variable
                       whose value is to be retrieved

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zget(variable_name)

    def kick(self, zserv_name, player_number, reason='rofl'):
        """Kicks a player from the zserv.

        zserv_name:    a string representing the name of the ZServ to
                       kick the player from
        player_number: a string representing the number of the player
                       to kick
        reason:        a string representing the reason for the kick

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zkick(player_number, reason)

    def killban(self, zserv_name, ip_address):
        """Removes a ban.

        zserv_name: a string representing the name of the ZServ to
                    remove the ban from
        ip_address: a string representing the IP address to remove the
                    ban for

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zkillban(ip_address)

    def map(self, zserv_name, map_number):
        """Changes the current map.

        zserv_name: a string representing the name of the ZServ to
                    change the map on
        map_number: a string representing the number of the map to
                    change to

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zmap(map_number)

    def maplist(self, zserv_name):
        """Returns the maplist.

        zserv_name: a string representing the name of the ZServ to
                    retrieve the maplist for

        Returns a list of strings representing the numbers of the maps
        in the maplist.

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zmaplist()

    def players(self, zserv_name):
        """Returns a list of players and their info.

        zserv_name: a string representing the name of the ZServ to
                    list the players for

        Returns a list of strings representing the number, name, and
        IP address of all players.

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zplayers()

    def removebots(self, zserv_name):
        """Removes all bots.

        zserv_name: a string representing the name of the ZServ to
                    remove the bots from

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zremovebots()

    def resetscores(self, zserv_name):
        """Resets all scores.

        zserv_name: a string representing the name of the ZServ to
                    reset the scores for

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zresetscores()

    def say(self, zserv_name, message):
        """Sends a message from "] CONSOLE [".

        zserv_name: a string representing the name of the ZServ to
                    send the message to
        message:    a string, the message to send

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zsay(message)

    def set(self, zserv_name, variable_name, variable_value):
        """Sets the value of a variable

        zserv_name:     a string representing the name of the ZServ
        variable_name:  a string representing the name of the variable
                        to set
        variable_value: a string representing the new value of the
                        variable

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zset(variable_name, variable_value)

    def toggle(self, zserv_name, boolean_variable):
        """Toggles a boolean option.

        zserv_name:       a string representing the name of the ZServ
        boolean_variable: a string representing the name of the
                          boolean variable to toggle on or off

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).ztoggle(boolean_variable)

    def unset(self, zserv_name, variable_name):
        """Unsets a variable (removes it).

        zserv_name:    a string representing the name of the ZServ to
                       remove the variable from
        variable_name: the name of the variable to unset

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zunset(variable_name)

    def wads(self, zserv_name):
        """Returns a list of the used WADs.

        zserv_name: a string representing the name of the ZServ to add
                    the bot to

        Returns a list of strings representing the names of the used
        WADs.

        """
        # logging.debug('')
        return self.get_zserv(zserv_name).zwads()

    def register_functions(self):
        """Registers RPC functions."""
        # logging.debug('')
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

