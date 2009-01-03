import Queue
import logging

from ZDStack import get_plugins
from ZDStack.Frag import Frag
from ZDStack.Utils import start_thread

class LogListener:

    classname = 'LogListener'

    def __init__(self, name):
        """Initializes a LogListener.

        name: a string representing the name of this LogListener

        """
        self.name = name
        self.events = Queue.Queue()
        self.last_event = None
        self.event_types_to_handlers = {'error': self.handle_error_event}
        self.keep_listening = False
        self.listener_thread = None

    def start(self):
        """Starts listening."""
        logging.debug('')
        self.keep_listening = True
        self.listener_thread = start_thread(self.handle_event,
                                            "%s listener thread" % self.name)

    def stop(self):
        """Stops listening."""
        logging.debug('')
        self.keep_listening = False
        # self.listener_thread.join()
        # self.listener_thread = None

    def __str__(self):
        return "<%s: %s>" % (self.classname, self.name)

    def __repr__(self):
        return '%s(%s)' % (self.classname, self.name)

    def handle_event(self):
        """Continuously handles an event.
        
        This method is called by a thread spawned by start().
        
        """
        while self.keep_listening:
            event = self.events.get()
            if event.type != 'junk':
                logging.getLogger('').debug("Handling event: %s" % (event.type))
            self._handle_event(event)

    def _handle_event(self, event):
        """Handles an event.

        event: a LogEvent instance.

        """
        if not event.type in self.event_types_to_handlers:
            self.handle_unhandled_event(event)
        else:
            self.event_types_to_handlers[event.type](event)
        if event.type != 'junk':
            self.last_event = event

    def handle_error_event(self, event):
        """Handles an error event.

        event: a LogEvent instance.

        """
        raise Exception(event.data['error'])

    def handle_unhandled_event(self, event):
        """Handles an unhandled event.

        event: a LogEvent instance.

        """
        return
        # raise Exception("Unhandled event: %s" % (event)) # for debugging

class ZServLogListener(LogListener):

    classname = 'ZServLogListener'

    def __init__(self, name, zserv):
        """Initializes a ZServLogListener.

        name:  a string representing the name of this LogListener
        zserv: a ZServ instance.

        """
        self.zserv = zserv
        LogListener.__init__(self, name)
        self.event_types_to_handlers['log_roll'] = self.handle_log_roll_event

    def __str__(self):
        return "<%s for [%s]: %s>" % (self.classname, self.zserv, self.name)

    def handle_log_roll_event(self, event):
        """Handles a log_roll event.

        event: a LogEvent instance.

        """
        self.zserv.roll_log(event.data['log'])

    def handle_error_event(self, event):
        """Handles an error event.

        event: a LogEvent instance.

        """
        logging.info("Event error: %s" % (event.data['error']))
        logging.getLogger('').info("Event traceback: \n%s\n" % (event.data['traceback']))

    def handle_unhandled_event(self, event):
        """Handles an unhandled event.

        event: a LogEvent instance.

        """
        pass # do nothing... actually do not handle the event

class PluginLogListener(ZServLogListener):

    def __init__(self, zserv, enabled_plugins):
        """Initializes a PluginLogListener.

        zserv:           a ZServ instance
        enabled_plugins: a list of strings representing the names of
                         all enabled plugins

        """
        ZServLogListener.__init__(self, 'Plugin Log Listener', zserv)
        plugins = get_plugins()
        self.plugins = [x for x in plugins if x.__name__ in enabled_plugins]
        for p in self.plugins:
            logging.getLogger('').debug("PLL Loaded Plugin [%s]" % (p.__name__))

    def _handle_event(self, event):
        """Handles an event.

        event: a LogEvent instance.

        """
        for plugin in self.plugins:
            logging.getLogger('').debug("Running plugin: %s" % (plugin.__name__))
            try:
                plugin(event, self.zserv)
            except Exception, e:
                raise
                es = "Exception in plugin %s: [%s]"
                logging.getLogger('').info(es % (plugin.__name__, e))

class ConnectionLogListener(ZServLogListener):

    def __init__(self, zserv):
        """Initializes a ConnectionLogListener.

        zserv: a ZServ instance.

        """
        ZServLogListener.__init__(self, 'Connection Log Listener', zserv)
        self.event_types_to_handlers['ip_log'] = self.handle_ip_log_event

    def handle_log_roll_event(self, event):
        """Handles a log_roll event.

        event: a LogEvent instance.

        """
        self.zserv.set_connection_log_filename(roll=True)

    def handle_ip_log_event(self, event):
        """Handles an ip_log event.

        event: a LogEvent instance.

        """
        logging.getLogger('').debug("Logging %s:%s" % (event.data['player'],
                                                       event.data['ip_address']))
        print "Logging %s:%s" % (event.data['player'], event.data['ip_address'])
        self.zserv.log_ip(event.data['player'], event.data['ip_address'])

class GeneralLogListener(ZServLogListener):

    def __init__(self, zserv):
        """Initializes a GeneralLogListener.

        zserv: a ZServ instance.

        """
        ZServLogListener.__init__(self, 'General Log Listener', zserv)
        self.event_types_to_handlers['message'] = self.handle_message_event
        self.event_types_to_handlers['team_switch'] = \
                                                self.handle_team_switch_event
        self.event_types_to_handlers['rcon_denied'] = \
                                                self.handle_rcon_denied_event
        self.event_types_to_handlers['rcon_granted'] = \
                                                self.handle_rcon_granted_event
        self.event_types_to_handlers['rcon_action'] = \
                                                self.handle_rcon_action_event
        self.event_types_to_handlers['flag_touch'] = \
                                                self.handle_flag_touch_event
        self.event_types_to_handlers['flag_loss'] = \
                                                self.handle_flag_loss_event
        self.event_types_to_handlers['flag_cap'] = \
                                                self.handle_flag_cap_event
        self.event_types_to_handlers['flag_return'] = \
                                                self.handle_flag_return_event
        self.event_types_to_handlers['flag_pick'] = \
                                                self.handle_flag_pick_event
        self.event_types_to_handlers['map_change'] = \
                                                self.handle_map_change_event
        self.event_types_to_handlers['frag'] = self.handle_frag_event
        self.event_types_to_handlers['death'] = self.handle_frag_event
        self.event_types_to_handlers['connection'] = \
                                                self.handle_connection_event
        self.event_types_to_handlers['disconnection'] = \
                                                self.handle_disconnection_event
        self.event_types_to_handlers['player_lookup'] = \
                                                self.handle_player_lookup_event
        self.event_types_to_handlers['game_join'] = self.handle_game_join_event
        self.event_types_to_handlers['team_join'] = self.handle_game_join_event
        self.lost_flag = []

    def handle_connection_event(self, event):
        """Handles a connection event.

        event: a LogEvent instance.

        """
        logging.debug("Connection Event: %s" % (str(event.data)))
        # self.zserv.add_player(event.data['player_name'])
        self.zserv.add_player(event.data['ip_address'], event.data['port'])

    def handle_player_lookup_event(self, event):
        """Handles a player_lookup event.

        event: a LogEvent instance.

        """
        self.zserv.update_player_numbers_and_ips()

    def handle_log_roll_event(self, event):
        """Handles a log_roll event.

        event: a LogEvent instance.

        """
        self.zserv.set_general_log_filename(roll=True)

    def handle_disconnection_event(self, event):
        """Handles a disconnection event.

        event: a LogEvent instance.

        """
        self.zserv.remove_player(event.data['player'])

    def handle_game_join_event(self, event):
        """Handles a game_join event.

        event: a LogEvent instance.

        """
        if not self.zserv.should_remember:
            self.zserv.should_remember = True
        try:
            player = self.zserv.get_player(event.data['player'])
        except ValueError:
            es = "Received a %s event for non-existent player [%s]"
            logging.info(es % (event.type, event.data['player']))
            return
        player.playing = True
        if event.type == 'team_join':
            try:
                team = self.zserv.get_team(event.data['team'])
            except ValueError:
                es = "Received a team join event to non-existent team [%s]"
                logging.info(es % (event.data['team']))
                return
            player.set_team(team)

    def handle_frag_event(self, event):
        """Handles a frag event.

        event: a LogEvent instance.

        """
        try:
            fraggee = self.zserv.get_player(event.data['fraggee'])
        except ValueError:
            es = "Received a death event for non-existent player [%s]"
            logging.info(es % (event.data['fraggee']))
            return
        if event.data['fraggee'] in self.lost_flag:
            fragged_runner = True
            self.lost_flag = []
        else:
            fragged_runner = False
        try:
            frag = Frag(event.data['fragger'], event.data['fraggee'],
                        event.data['weapon'], fragged_runner=fragged_runner)
        except:
            print "Broken Frag Event: %r, %s" % (event, event.line)
            raise
        fraggee.add_death(frag)
        # if self.last_event.type == 'flag_loss':
        #     fraggee.add_flag_loss(frag)
        if event.type == 'frag': # no suicides
            try:
                fragger = self.zserv.get_player(event.data['fragger'])
            except ValueError:
                es = "Received a frag event for non-existent player [%s]"
                logging.info(es % (event.data['fragger']))
                return
            fragger.add_frag(frag)
            if self.last_event.type == 'flag_loss':
                fragger.add_flag_drop(frag)

    def handle_message_event(self, event):
        """Handles a message event.

        event: a LogEvent instance.

        """
        self.zserv.handle_message(event.data['message'],
                                  event.data['messenger'])

    def handle_team_switch_event(self, event):
        """Handles a team_switch event.

        event: a LogEvent instance.

        """
        try:
            team = self.zserv.get_team(event.data['team'])
        except ValueError:
            es = "Received a team switch event to non-existent team [%s]"
            logging.info(es % (event.data['team']))
            return
        try:
            self.zserv.get_player(event.data['player']).set_team(team)
        except ValueError:
            es = "Received a team switch event for non-existent player [%s]"
            logging.info(es % (event.data['player']))

    def handle_rcon_granted_event(self, event):
        """Handles an rcon_granted event.

        event: a LogEvent instance.

        """
        try:
            self.zserv.get_player(event.data['player']).add_rcon_access()
        except ValueError:
            es = "Received an RCON access event for non-existent player [%s]"
            logging.info(es % (event.data['player']))

    def handle_rcon_denied_event(self, event):
        """Handles an rcon_denied event.

        event: a LogEvent instance.

        """
        try:
            self.zserv.get_player(event.data['player']).add_rcon_denial()
        except ValueError:
            es = "Received a RCON denial event for non-existent player [%s]"
            logging.info(es % (event.data['player']))

    def handle_rcon_action_event(self, event):
        """Handles an rcon_action event.

        event: a LogEvent instance.

        """
        action = event.data['action']
        try:
            self.zserv.get_player(event.data['player']).add_rcon_action(action)
        except ValueError:
            es = "Received an RCON action event for non-existent player [%s]"
            logging.info(es % (event.data['player']))

    def handle_flag_touch_event(self, event):
        """Handles a flag_touch event.

        event: a LogEvent instance.

        """
        try:
            player = self.zserv.get_player(event.data['player'])
        except ValueError:
            es = "Received a flag touch event for non-existent player [%s]"
            logging.info(es % (event.data['player']))
            return
        player.set_has_flag(True)
        player.add_flag_touch()

    def handle_flag_loss_event(self, event):
        """Handles a flag_loss event.

        event: a LogEvent instance.

        """
        try:
            runner = self.zserv.get_player(event.data['player'])
        except ValueError:
            es = "Received a flag loss event for non-existent player [%s]"
            logging.info(es % (event.data['player']))
            return
        runner.set_has_flag(False)
        self.lost_flag.append(runner.name)

    def handle_flag_cap_event(self, event):
        """Handles a flag_cap event.

        event: a LogEvent instance.

        """
        try:
            player = self.zserv.get_player(event.data['player'])
        except ValueError:
            es = "Received a flag cap event for non-existent player [%s]"
            logging.info(es % (event.data['player']))
            return
        player.add_flag_cap()
        player.set_has_flag(False)

    def handle_flag_return_event(self, event):
        """Handles a flag_return event.

        event: a LogEvent instance.

        """
        try:
            self.zserv.get_player(event.data['player']).add_flag_return()
        except ValueError:
            es = "Received a flag return event for non-existent player [%s]"
            logging.info(es % (event.data['player']))

    def handle_flag_pick_event(self, event):
        """Handles a flag_pick event.

        event: a LogEvent instance.

        """
        try:
            player = self.zserv.get_player(event.data['player'])
        except ValueError:
            es = "Received a flag pick event for non-existent player [%s]"
            logging.info(es % (event.data['player']))
            return
        player.add_flag_pick()
        player.set_has_flag(True)

    def handle_map_change_event(self, event):
        """Handles a map_change event.

        event: a LogEvent instance.

        """
        self.zserv.change_map(event.data['number'], event.data['name'])

