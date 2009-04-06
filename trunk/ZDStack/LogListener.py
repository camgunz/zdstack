from __future__ import with_statement

import Queue
import logging
import datetime
import traceback

from elixir import session

from threading import Lock

from ZDStack import ZDSThreadPool
from ZDStack import DIE_THREADS_DIE, MAX_TIMEOUT, TEAM_COLORS, TICK, \
                    PlayerNotFoundError, get_plugins
from ZDStack.ZDSModels import get_weapon, Round, Alias, Frag, FlagTouch, \
                              FlagReturn, RCONAccess, RCONDenial, RCONAction

from sqlalchemy import desc

class BaseLogListener(object):

    classname = 'BaseLogListener'

    def __init__(self, name, zserv):
        """Initializes a BaseLogListener.

        name:  a string representing the name of this LogListener
        zserv: a ZServ instance.

        """
        logging.debug('')
        self.name = name
        self.zserv = zserv
        self.generic_events = Queue.Queue()
        self.command_events = Queue.Queue()
        self.keep_listening = False
        self.command_listener_thread = None
        self.generic_listener_thread = None
        self.event_types_to_handlers = dict()
        self.set_handler('error', self.handle_error_event)

    def set_handler(self, event_type, handler):
        """Sets the handler method for a certain event_type.

        event_type: a string representing the type of event to handle.
        handler:    a function that will handle the event, takes an
                    event instance as its only argument.

        """
        self.event_types_to_handlers[event_type] = handler

    def start(self):
        """Starts listening."""
        logging.debug('')
        self.keep_listening = True
        ct = self.start_handling_command_events
        cn = '%s command listener thread' % (self.name)
        gt = self.start_handling_generic_events
        gn = '%s generic listener thread' % (self.name)
        kg = lambda: self.keep_listening == True
        self.command_listener_thread = ZDSThreadPool.get_thread(target=ct,
                                                                name=cn,
                                                                keep_going=kg)
        self.generic_listener_thread = ZDSThreadPool.get_thread(target=gt,
                                                                name=gn,
                                                                keep_going=kg)

    def stop(self):
        """Stops listening."""
        logging.debug('')
        self.keep_listening = False
        if self.command_listener_thread:
            ZDSThreadPool.join(self.command_listener_thread)
        if self.generic_listener_thread:
            ZDSThreadPool.join(self.generic_listener_thread)
        logging.debug("Joined all listener threads")

    def __str__(self):
        return "<%s: %s>" % (self.classname, self.name)

    def __repr__(self):
        return '%s(%s)' % (self.classname, self.name)

    def start_handling_command_events(self):
        """Starts handling command events.

        This method is called by a thread spawned by start().

        """
        self._start_handling_events(self.generic_events)

    def start_handling_generic_events(self):
        """Starts handling generic events.

        This method is called by a thread spawned by start().

        """
        self._start_handling_events(self.command_events)

    def _start_handling_events(self, queue):
        """Starts handling events.

        queue: a Queue instance.
        
        This method is called by a thread spawned by start().
        
        """
        try:
            event = queue.get(timeout=MAX_TIMEOUT)
        except Queue.Empty:
            ###
            # If we're shutting down, this thread will wait forever on an
            # event that will never come.  So make this thread check every
            # second that it should keep listening.
            ###
            return
        s = "Handling %s event (Line: [%s])" % (event.type, event.line)
        logging.debug(s)
        try:
            self._handle_event(event)
            logging.debug("Finished handling %s event" % (event.type))
        except Exception, e:
            ###
            # I suppose we should just log the error and keep handling
            # events... but I haven't really thought a lot about it.
            ###
            es = "Error while handling %s event: %s\n\nTraceback:\n\n%s"
            logging.error(es % (event.type, e, traceback.format_exc()))

    def _handle_event(self, event):
        """Handles an event.

        event: a LogEvent instance.

        """
        try:
            handler = self.event_types_to_handlers[event.type]
        except KeyError:
            logging.debug("No handler set for %s" % (event.type))
            handler = self.handle_unhandled_event
        try:
            handler(event)
        except Exception, e:
            logging.debug("Exception!: %s" % (e))
            raise

    def handle_error_event(self, event):
        """Handles an error event.

        event: a LogEvent instance.

        """
        ###
        # Should we really raise an exception here?  I think the rest of the
        # code doesn't assume that event handling stops on an error, so we
        # should at least correct that inconsistency.
        ###
        raise Exception(event.data['error'])

    def __str__(self):
        return "<%s for [%s]: %s>" % (self.classname, self.zserv, self.name)

    def handle_error_event(self, event):
        """Handles an error event.

        event: a LogEvent instance.

        """
        logging.error("Event error: %s" % (event.data['error']))
        logging.error("Event traceback: \n%s\n" % (event.data['traceback']))

    def handle_unhandled_event(self, event):
        """Handles an unhandled event.

        event: a LogEvent instance.

        """
        pass # do nothing... actually do not handle the event

class PluginLogListener(BaseLogListener):

    classname = 'PluginLogListener'

    def __init__(self, zserv):
        """Initializes a PluginLogListener.

        zserv: a ZServ instance

        """
        BaseLogListener.__init__(self, 'Plugin Log Listener', zserv)
        plugins = get_plugins()
        self.plugins = [x for x in plugins if x.__name__ in self.zserv.plugins]
        for p in self.plugins:
            logging.debug("PLL Loaded Plugin [%s]" % (p.__name__))

    def _handle_event(self, event):
        """Handles an event.

        event: a LogEvent instance.

        """
        for plugin in self.plugins:
            logging.debug("Running plugin: %s" % (plugin.__name__))
            try:
                plugin(event, self.zserv)
            except Exception, e:
                raise
                es = "Exception in plugin %s: [%s]"
                logging.error(es % (plugin.__name__, e))

class GeneralLogListener(BaseLogListener):

    classname = 'GeneralLogListener'

    def __init__(self, zserv):
        """Initializes a GeneralLogListener.

        zserv: a ZServ instance.

        """
        BaseLogListener.__init__(self, 'General Log Listener', zserv)
        self.set_handler('connection', self._sync_players)
        self.set_handler('disconnection', self._sync_players)
        self.set_handler('player_lookup', self._sync_players)
        self.set_handler('game_join', self.handle_game_join_event)
        self.set_handler('team_join', self.handle_game_join_event)
        self.set_handler('team_switch', self.handle_game_join_event)
        self.set_handler('rcon_denied', self.handle_rcon_event)
        self.set_handler('rcon_granted', self.handle_rcon_event)
        self.set_handler('rcon_action', self.handle_rcon_event)
        self.set_handler('flag_touch', self.handle_flag_event)
        self.set_handler('flag_pick', self.handle_flag_event)
        self.set_handler('flag_cap', self.handle_flag_event)
        self.set_handler('flag_loss', self.handle_flag_event)
        self.set_handler('flag_return', self.handle_flag_return_event)
        self.set_handler('map_change', self.handle_map_change_event)
        self.set_handler('frag', self.handle_frag_event)
        self.set_handler('death', self.handle_frag_event)
        self.state_lock = Lock()
        self.clear_state() # Adds some instance variables too

    def _handle_event(self, event):
        """Handles an event.

        event: a LogEvent instance.

        """
        with self.state_lock:
            BaseLogListener._handle_event(self, event)

    def clear_state(self, acquire_lock=True):
        """Clears the current state of the round."""
        def blah():
            self.players_holding_flags = list()
            self.teams_holding_flags = list()
            self.fragged_runners = list()
            self.team_scores = dict()
            self.team_scores.update({'red': 0, 'blue': 0, 'green': 0,
                                     'white': 0})
        if acquire_lock:
            with self.state_lock:
                blah()
        else:
            blah()

    def stop(self):
        """Stops a GeneralLogListener."""
        BaseLogListener.stop(self)
        with self.state_lock:
            self.clear_state()

    def _sync_players(self, event):
        logging.debug("_sync_players(%s)" % (event))
        self.zserv.sync_players(sleep=3.0)

    def handle_game_join_event(self, event):
        """Handles a game_join event.

        event: a LogEvent instance.

        """
        logging.debug("handle_game_join_event(%s)" % (event))
        try:
            player = self.zserv.players.get(event.data['player'])
        except PlayerNotFoundError:
            if event.type[0] in 'aeiou':
                es = "Received an %s event for non-existent player [%s]"
            else:
                es = "Received a %s event for non-existent player [%s]"
            logging.error(es % (event.type, event.data['player']))
            return
        if event.type in ('team_join', 'team_switch'):
            color = event.data['team']
            self.zserv.teams.add(color)
            self.zserv.teams.set_player_team(player, color)
        else:
            with self.zserv.players.lock:
                player.playing = True

    def handle_rcon_event(self, event):
        """Handles an RCON-related event.

        event: a LogEvent instance.

        """
        logging.debug("handle_rcon_event(%s)" % (event))
        try:
            player = self.zserv.players.get(event.data['player'])
        except PlayerNotFoundError:
            es = "Received an RCON event for non-existent player [%s]"
            logging.error(es % (event.data['player']))
            return
        if event.type == 'rcon_denied':
            s = RCONDenial(player=player.alias, round=self.zserv.round,
                           timestamp=event.dt)
        elif event.type == 'rcon_granted':
            s = RCONAccess(player=player.alias, round=self.zserv.round,
                           timestamp=event.dt)
        elif event.type == 'rcon_action':
            s = RCONAction(player=player.alias, round=self.zserv.round,
                           timestamp=event.dt, action=event.data['action'])
        logging.debug("Putting %s in session" % (s))
        session.add(s)

    def _get_latest_flag_touch(self, player):
        """Returns the latest FlagTouch for a player.

        player: a Player instance.

        """
        q = session.query(FlagTouch)
        q = q.filter(Alias.name==player.name)
        q = q.filter(Round.id==self.zserv.round.id)
        q = q.order_by(desc(FlagTouch.touch_time))
        ft =  q.first() # this should be the runner's latest FlagTouch
        if not ft:
            raise Exception("No FlagTouch by %s found" % (player.name))
        return ft

    def handle_flag_event(self, event):
        """Handles a flag_touch event.

        event: a LogEvent instance.

        """
        logging.debug("handle_flag_event(%s)" % (event))
        try:
            runner = self.zserv.players.get(event.data['player'])
        except PlayerNotFoundError:
            es = "Received a flag touch event for non-existent player [%s]"
            logging.error(es % (event.data['player']))
            return
        self.players_holding_flags.append(runner)
        tc = self.zserv.teams.get_player_team(runner)
        logging.debug("Found player's team: %s" % (tc.color))
        self.teams_holding_flags.append(tc.color)
        red_team_holding_flag = 'red' in self.teams_holding_flags
        blue_team_holding_flag = 'blue' in self.teams_holding_flags
        green_team_holding_flag = 'green' in self.teams_holding_flags
        white_team_holding_flag = 'white' in self.teams_holding_flags
        logging.debug("Before big IF")
        if event.type in ('flag_touch', 'flag_pick'):
            logging.debug("Event.type was either 'flag_touch' or 'flag_pick': %s" % (event.type))
            s = FlagTouch(player=runner.alias, round=self.zserv.round,
                          touch_time=event.dt,
                          was_picked=event.type=='flag_pick',
                          player_team_color=tc,
                          red_team_holding_flag=red_team_holding_flag,
                          blue_team_holding_flag=blue_team_holding_flag,
                          green_team_holding_flag=green_team_holding_flag,
                          white_team_holding_flag=white_team_holding_flag,
                          red_team_score=self.team_scores['red'],
                          blue_team_score=self.team_scores['blue'],
                          green_team_score=self.team_scores['green'],
                          white_team_score=self.team_scores['white'])
            logging.debug("Putting %s in session" % (s))
            session.add(s)
        else:
            logging.debug("Event.type was not either 'flag_touch' or 'flag_pick': %s" % (event.type))
            ###
            # At this point, the event is either a flag_cap or flag_loss.
            ###
            s = self._get_latest_flag_touch(runner)
            s.loss_time = event.dt
            self.teams_holding_flags.remove(tc.color)
            self.players_holding_flags.remove(runner)
            if event.type == 'flag_cap':
                s.resulted_in_score = True
                self.team_scores[tc.color] += 1
            else: # flag_loss!
                s.resulted_in_score = False
                self.fragged_runners.append(runner)
            logging.debug("Merging %s, %s" % (s, s.loss_time))
            session.merge(s)
            logging.debug("Merged %s, %s" % (s, s.loss_time))

    def handle_flag_return_event(self, event):
        """Handles a flag_return event.

        event: a LogEvent instance.

        """
        logging.debug("handle_flag_return_event(%s)" % (event))
        try:
            player = self.zserv.players.get(event.data['player'])
        except PlayerNotFoundError:
            es = "Received a flag return event for non-existent player [%s]"
            logging.error(es % (event.data['player']))
        tc = self.zserv.teams.get_player_team(player)
        self.teams_holding_flags.append(tc.color)
        player_was_holding_flag = player in self.players_holding_flags
        red_team_holding_flag = 'red' in self.teams_holding_flags
        blue_team_holding_flag = 'blue' in self.teams_holding_flags
        green_team_holding_flag = 'green' in self.teams_holding_flags
        white_team_holding_flag = 'white' in self.teams_holding_flags
        if event.type in ('flag_touch', 'flag_pick'):
            s = FlagReturn(player=runner, round=self.zserv.round,
                           timestamp=event.dt,
                           player_was_holding_flag=player_was_holding_flag,
                           player_team_color=tc,
                           red_team_holding_flag=red_team_holding_flag,
                           blue_team_holding_flag=blue_team_holding_flag,
                           green_team_holding_flag=green_team_holding_flag,
                           white_team_holding_flag=white_team_holding_flag,
                           red_team_score=self.team_scores['red'],
                           blue_team_score=self.team_scores['blue'],
                           green_team_score=self.team_scores['green'],
                           white_team_score=self.team_scores['white'])
            logging.debug("Putting %s in session" % (s))
            session.add(s)

    def handle_frag_event(self, event):
        """Handles a frag event.

        event: a LogEvent instance.

        """
        logging.debug("handle_frag_event(%s)" % (event))
        try:
            fraggee = self.zserv.players.get(event.data['fraggee'])
        except PlayerNotFoundError:
            es = "Received a death event for non-existent player [%s]"
            logging.error(es % (event.data['fraggee']))
            return
        if 'fragger' in event.data:
            try:
                fragger = self.zserv.players.get(event.data['fragger'])
            except PlayerNotFoundError:
                es = "Received a death event for non-existent player [%s]"
                logging.error(es % (event.data['fragger']))
                return
            is_suicide = False
        else:
            fragger = fraggee
            is_suicide = True
        weapon = get_weapon(name=event.data['weapon'], is_suicide=is_suicide)
        if fraggee in self.fragged_runners:
            fraggee_was_holding_flag = True
            self.fragged_runners.remove(fraggee)
        else:
            fraggee_was_holding_flag = False
        fraggee_team = self.zserv.teams.get_player_team(fraggee)
        if is_suicide:
            fragger_was_holding_flag = fraggee_was_holding_flag
            fragger_team = fraggee_team
        else:
            fragger_was_holding_flag = fragger in self.players_holding_flags
            fragger_team = self.zserv.teams.get_player_team(fragger)
        red_team_holding_flag = 'red' in self.teams_holding_flags
        blue_team_holding_flag = 'blue' in self.teams_holding_flags
        green_team_holding_flag = 'green' in self.teams_holding_flags
        white_team_holding_flag = 'white' in self.teams_holding_flags
        f = Frag(fragger=fragger.alias, fraggee=fraggee.alias, weapon=weapon,
                 round=self.zserv.round, timestamp=event.dt,
                 fragger_was_holding_flag=fragger_was_holding_flag,
                 fraggee_was_holding_flag=fraggee_was_holding_flag,
                 fragger_team_color=fragger_team,
                 fraggee_team_color=fraggee_team,
                 red_team_holding_flag=red_team_holding_flag,
                 blue_team_holding_flag=blue_team_holding_flag,
                 green_team_holding_flag=green_team_holding_flag,
                 white_team_holding_flag=white_team_holding_flag,
                 red_team_score=self.team_scores['red'],
                 blue_team_score=self.team_scores['blue'],
                 green_team_score=self.team_scores['green'],
                 white_team_score=self.team_scores['white'])
        logging.debug("Putting %s in session" % (f))
        session.add(f)

    def handle_map_change_event(self, event):
        """Handles a map_change event.

        event: a LogEvent instance.

        """
        logging.debug("handle_map_change_event(%s)" % (event))
        self.zserv.change_map(event.data['number'], event.data['name'])
        ###
        # All event handlers run with the state lock already acquired.
        ###
        self.clear_state(acquire_lock=False)

class FakeLogListener(GeneralLogListener):

    classname = 'FakeLogListener'

    def __init__(self, zserv):
        """Initializes a FakeLogListener.

        zserv: a ZServ instance.

        """
        GeneralLogListener.__init__(self, zserv)
        self.set_handler('map_change', self.handle_map_change)
        self.set_handler('connection', self.handle_connection)
        self.set_handler('disconnection', self.handle_disconnection)
        self.set_handler('player_lookup', self.handle_player_lookup_event)
        self.set_handler('players_command', self.handle_players_command_event)

    def handle_map_change(self, event):
        dl = \
"======================================================================"
        self.zserv.players = []
        self.zserv.send_line(dl)
        self.zserv.send_line('map%s: %s' % (str(event.data['number']).zfill(2),
                                            event.data['name']))
        self.zserv.send_line(dl)

    def handle_connection(self, event):
        self.zserv.players.add(event.data['ip_address'], event.data['port'])
        self.zserv.send_line(event.line)

    def handle_disconnection(self, event):
        self.zserv.players.remove(event.data['player'])
        self.zserv.send_line(event.line)

    def handle_player_lookup_event(self, event):
        pn = event.data['player_name']
        self.zserv.players.get(pn).set_name(pn)
        self.zserv.send_line(event.line)

    def handle_players_command_event(self, event):
        self.zserv.update_player(event.data['player_ip'],
                                 event.data['player_port'],
                                 event.data['player_num'],
                                 event.data['player_name'])
        self.zserv.send_players()

    def handle_unhandled_event(self, event):
        """Handles an unhandled event.

        event: a LogEvent instance.

        """
        self.zserv.send_line(event.line)

