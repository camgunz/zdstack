from __future__ import with_statement

import Queue
import logging
import datetime
import traceback

from elixir import session

from ZDStack import ZDSThreadPool
from ZDStack import DIE_THREADS_DIE, MAX_TIMEOUT, TEAM_COLORS, TICK, \
                    PlayerNotFoundError, get_db_lock, get_plugins
from ZDStack.ZDSModels import get_weapon, Round, Alias, Frag, FlagTouch, \
                              FlagReturn, RCONAccess, RCONDenial, RCONAction

from sqlalchemy import desc

class BaseEventHandler(object):

    def __init__(self):
        """Initializes a BaseEventHandler."""
        logging.debug('')
        self._event_types_to_handlers = dict()
        self.set_handler('error', self.handle_error_event)

    def get_handler(self, event_type):
        """Returns a handler method for a given event_type.

        event_type: a string representing thetype of event to handle.

        """
        return self._event_types_to_handlers.get(event_type,
                                                 self.handle_unhandled_event)

    def set_handler(self, event_type, handler):
        """Sets the handler method for a certain event_type.

        event_type: a string representing the type of event to handle.
        handler:    a function that will handle the event, takes an
                    event instance as its only argument.

        """
        self._event_types_to_handlers[event_type] = handler

    def handle_error_event(self, event, zserv=None):
        """Handles an error event.

        event: a LogEvent instance.
        zserv: the ZServ instance that generated the event.

        """
        ###
        # Should we really raise an exception here?  I think the rest of the
        # code doesn't assume that event handling stops on an error, so we
        # should at least correct that inconsistency.
        ###
        raise Exception(event.data['error'])

    def handle_error_event(self, event, zserv=None):
        """Handles an error event.

        event: a LogEvent instance.
        zserv: the ZServ instance that generated the event.

        """
        logging.error("Event error: %s" % (event.data['error']))
        logging.error("Event traceback: \n%s\n" % (event.data['traceback']))

    def handle_unhandled_event(self, event, zserv):
        """Handles an unhandled event.

        event: a LogEvent instance.
        zserv: the ZServ instance that generated the event.

        """
        pass # do nothing... actually do not handle the event

class ZServEventHandler(BaseEventHandler):

    def __init__(self):
        """Initializes a ZServEventHandler."""
        BaseEventHandler.__init__(self)
        ###
        # A 'connection' event has no player name, only an IP address and a
        # port.  So in order to be meaningful, we must wait until the zserv
        # process assigns that connection a name.  This happens with game_join,
        # team_join, and player_lookup events.
        #
        # self.set_handler('connection', self._sync_players)
        #
        ###
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

    def _sync_players(self, event, zserv):
        """Syncs players.

        event: a LogEvent instance.
        zserv: the ZServ instance that generated the event.

        """
        logging.debug("_sync_players(%s)" % (event))
        ###
        # This used to wait 3 seconds between obtaining the zserv's STDIN lock
        # and sync'ing the players list.  That is way, way too long now.
        #
        # zserv.sync_players(sleep=3.0)
        #
        ###
        zserv.players.sync()

    def handle_game_join_event(self, event, zserv):
        """Handles a game_join event.

        event: a LogEvent instance.
        zserv: the ZServ instance that generated the event.

        """
        logging.debug("handle_game_join_event(%s)" % (event))
        try:
            player = zserv.players.get(event.data['player'])
        except PlayerNotFoundError:
            if event.type[0] in 'aeiou':
                es = "Received an %s event for non-existent player [%s]"
            else:
                es = "Received a %s event for non-existent player [%s]"
            logging.error(es % (event.type, event.data['player']))
            return
        if event.type in ('team_join', 'team_switch'):
            color = event.data['team']
            zserv.teams.add(color)
            zserv.teams.set_player_team(player, color)
        else:
            with zserv.players.lock:
                player.playing = True

    def handle_rcon_event(self, event, zserv):
        """Handles an RCON-related event.

        event: a LogEvent instance.
        zserv: the ZServ instance that generated the event.

        """
        logging.debug("handle_rcon_event(%s)" % (event))
        try:
            player = zserv.players.get(event.data['player'])
        except PlayerNotFoundError:
            es = "Received an RCON event for non-existent player [%s]"
            logging.error(es % (event.data['player']))
            return
        with get_db_lock():
            if event.type == 'rcon_denied':
                s = RCONDenial(player=player.alias, round=zserv.round,
                               timestamp=event.dt)
            elif event.type == 'rcon_granted':
                s = RCONAccess(player=player.alias, round=zserv.round,
                               timestamp=event.dt)
            elif event.type == 'rcon_action':
                s = RCONAction(player=player.alias, round=zserv.round,
                               timestamp=event.dt, action=event.data['action'])
            logging.debug("Putting %s in session" % (s))
            session.add(s)
            session.commit()

    def _get_latest_flag_touch(self, player, round):
        """Returns the latest FlagTouch for a player.

        player: a Player instance.
        round:  the Round where the FlagTouch occurred.

        """
        q = session.query(FlagTouch)
        q = q.filter(Alias.name==player.name)
        q = q.filter(Round.id==round.id)
        q = q.order_by(desc(FlagTouch.touch_time))
        ft =  q.first() # this should be the runner's latest FlagTouch
        if not ft:
            raise Exception("No FlagTouch by %s found" % (player.name))
        return ft

    def handle_flag_event(self, event, zserv):
        """Handles a flag_touch event.

        event: a LogEvent instance.
        zserv: the ZServ instance that generated the event.

        """
        logging.debug("handle_flag_event(%s)" % (event))
        try:
            runner = zserv.players.get(event.data['player'])
        except PlayerNotFoundError:
            es = "Received a flag touch event for non-existent player [%s]"
            logging.error(es % (event.data['player']))
            return
        tc = zserv.teams.get_player_team(runner)
        logging.debug("Found player's team: %s" % (tc.color))
        with zserv.state_lock:
            red_team_holding_flag = 'red' in zserv.teams_holding_flags
            blue_team_holding_flag = 'blue' in zserv.teams_holding_flags
            green_team_holding_flag = 'green' in zserv.teams_holding_flags
            white_team_holding_flag = 'white' in zserv.teams_holding_flags
            red_team_score = zserv.team_scores.get('red', None)
            blue_team_score = zserv.team_scores.get('blue', None)
            green_team_score = zserv.team_scores.get('green', None)
            white_team_score = zserv.team_scores.get('white', None)
            if event.type in ('flag_touch', 'flag_pick'):
                zserv.players_holding_flags.append(runner)
                zserv.teams_holding_flags.append(tc.color)
                s = FlagTouch(player=runner.alias, round=zserv.round,
                              touch_time=event.dt,
                              was_picked=event.type=='flag_pick',
                              player_team_color=tc,
                              red_team_holding_flag=red_team_holding_flag,
                              blue_team_holding_flag=blue_team_holding_flag,
                              green_team_holding_flag=green_team_holding_flag,
                              white_team_holding_flag=white_team_holding_flag,
                              red_team_score=red_team_score,
                              blue_team_score=blue_team_score,
                              green_team_score=green_team_score,
                              white_team_score=white_team_score)
                session.add(s)
                session.commit()
            else:
                ###
                # At this point, the event is either a flag_cap or flag_loss.
                ###
                s = self._get_latest_flag_touch(runner, zserv.round)
                s.loss_time = event.dt
                zserv.teams_holding_flags.remove(tc.color)
                zserv.players_holding_flags.remove(runner)
                if event.type == 'flag_cap':
                    s.resulted_in_score = True
                    zserv.team_scores[tc.color] += 1
                else: # flag_loss!
                    s.resulted_in_score = False
                    zserv.fragged_runners.append(runner)
                logging.debug("Merging %s, %s" % (s, s.loss_time))
                session.merge(s)
                session.commit()
                logging.debug("Merged %s, %s" % (s, s.loss_time))

    def handle_flag_return_event(self, event, zserv):
        """Handles a flag_return event.

        event: a LogEvent instance.
        zserv: the ZServ instance that generated the event.

        """
        logging.debug("handle_flag_return_event(%s)" % (event))
        try:
            player = zserv.players.get(event.data['player'])
        except PlayerNotFoundError:
            es = "Received a flag return event for non-existent player [%s]"
            logging.error(es % (event.data['player']))
        tc = zserv.teams.get_player_team(player)
        with zserv.state_lock:
            zserv.teams_holding_flags.append(tc.color)
            player_was_holding_flag = player in zserv.players_holding_flags
            red_team_holding_flag = 'red' in zserv.teams_holding_flags
            blue_team_holding_flag = 'blue' in zserv.teams_holding_flags
            green_team_holding_flag = 'green' in zserv.teams_holding_flags
            white_team_holding_flag = 'white' in zserv.teams_holding_flags
            red_team_score = zserv.team_scores.get('red', None)
            blue_team_score = zserv.team_scores.get('blue', None)
            green_team_score = zserv.team_scores.get('green', None)
            white_team_score = zserv.team_scores.get('white', None)
            s = FlagReturn(player=runner, round=zserv.round,
                           timestamp=event.dt,
                           player_was_holding_flag=player_was_holding_flag,
                           player_team_color=tc,
                           red_team_holding_flag=red_team_holding_flag,
                           blue_team_holding_flag=blue_team_holding_flag,
                           green_team_holding_flag=green_team_holding_flag,
                           white_team_holding_flag=white_team_holding_flag,
                           red_team_score=red_team_score,
                           blue_team_score=blue_team_score,
                           green_team_score=green_team_score,
                           white_team_score=white_team_score)
            logging.debug("Putting %s in session" % (s))
            session.add(s)
            session.commit()

    def handle_frag_event(self, event, zserv):
        """Handles a frag event.

        event: a LogEvent instance.
        zserv: the ZServ instance that generated the event.

        """
        logging.debug("handle_frag_event(%s)" % (event))
        try:
            fraggee = zserv.players.get(event.data['fraggee'])
        except PlayerNotFoundError:
            es = "Received a death event for non-existent player [%s]"
            logging.error(es % (event.data['fraggee']))
            return
        fraggee_team = zserv.teams.get_player_team(fraggee)
        if 'fragger' in event.data:
            try:
                fragger = zserv.players.get(event.data['fragger'])
            except PlayerNotFoundError:
                es = "Received a frag event for non-existent player [%s]"
                logging.error(es % (event.data['fragger']))
                return
            is_suicide = False
        else:
            fragger = fraggee
            fragger_team = fraggee_team
            is_suicide = True
        weapon = get_weapon(name=event.data['weapon'], is_suicide=is_suicide)
        with zserv.state_lock:
            if fraggee in zserv.fragged_runners:
                fraggee_was_holding_flag = True
                zserv.fragged_runners.remove(fraggee)
            else:
                fraggee_was_holding_flag = False
            if is_suicide:
                fragger_was_holding_flag = fraggee_was_holding_flag
            else:
                fragger_was_holding_flag = fragger in zserv.players_holding_flags
            red_team_holding_flag = 'red' in zserv.teams_holding_flags
            blue_team_holding_flag = 'blue' in zserv.teams_holding_flags
            green_team_holding_flag = 'green' in zserv.teams_holding_flags
            white_team_holding_flag = 'white' in zserv.teams_holding_flags
            red_team_score = zserv.team_scores.get('red', None)
            blue_team_score = zserv.team_scores.get('blue', None)
            green_team_score = zserv.team_scores.get('green', None)
            white_team_score = zserv.team_scores.get('white', None)
            f = Frag(fragger=fragger.alias, fraggee=fraggee.alias,
                     weapon=weapon, round=zserv.round, timestamp=event.dt,
                     fragger_was_holding_flag=fragger_was_holding_flag,
                     fraggee_was_holding_flag=fraggee_was_holding_flag,
                     fragger_team_color=fragger_team,
                     fraggee_team_color=fraggee_team,
                     red_team_holding_flag=red_team_holding_flag,
                     blue_team_holding_flag=blue_team_holding_flag,
                     green_team_holding_flag=green_team_holding_flag,
                     white_team_holding_flag=white_team_holding_flag,
                     red_team_score=red_team_score,
                     blue_team_score=blue_team_score,
                     green_team_score=green_team_score,
                     white_team_score=white_team_score)
            logging.debug("Putting %s in session" % (f))
            session.add(f)
            session.commit()

    def handle_map_change_event(self, event, zserv):
        """Handles a map_change event.

        event: a LogEvent instance.
        zserv: the ZServ instance that generated the event.

        """
        logging.debug("handle_map_change_event(%s)" % (event))
        zserv.change_map(event.data['number'], event.data['name'])

class FakeEventHandler(ZServEventHandler):

    def __init__(self):
        """Initializes a FakeEventHandler."""
        ZServEventHandler.__init__(self, zserv)
        self.set_handler('map_change', self.handle_map_change)
        self.set_handler('connection', self.handle_connection)
        self.set_handler('disconnection', self.handle_disconnection)
        self.set_handler('player_lookup', self.handle_player_lookup_event)
        self.set_handler('players_command', self.handle_players_command_event)

    def handle_map_change(self, event, zserv):
        dl = \
"======================================================================"
        self.zserv.players = []
        self.zserv.send_line(dl)
        self.zserv.send_line('map%s: %s' % (str(event.data['number']).zfill(2),
                                            event.data['name']))
        self.zserv.send_line(dl)

    def handle_connection(self, event, zserv):
        self.zserv.players.add(event.data['ip_address'], event.data['port'])
        self.zserv.send_line(event.line)

    def handle_disconnection(self, event, zserv):
        self.zserv.players.remove(event.data['player'])
        self.zserv.send_line(event.line)

    def handle_player_lookup_event(self, event, zserv):
        pn = event.data['player_name']
        self.zserv.players.get(pn).set_name(pn)
        self.zserv.send_line(event.line)

    def handle_players_command_event(self, event, zserv):
        self.zserv.update_player(event.data['player_ip'],
                                 event.data['player_port'],
                                 event.data['player_num'],
                                 event.data['player_name'])
        self.zserv.send_players()

    def handle_unhandled_event(self, event, zserv):
        """Handles an unhandled event.

        event: a LogEvent instance.

        """
        self.zserv.send_line(event.line)

