from __future__ import with_statement

import datetime

from ZDStack import TICK, PlayerNotFoundError, get_session_class, get_zdslog
from ZDStack.ZServ import TEAM_MODES, TEAMDM_MODES
from ZDStack.ZDSModels import Round, Alias, Frag, FlagTouch, FlagReturn, \
                              RCONAccess, RCONDenial, RCONAction
from ZDStack.ZDSDatabase import get_weapon, get_alias, get_team_color, \
                                global_session, persist

from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound

zdslog = get_zdslog()

class BaseEventHandler(object):

    """The base EventHandler class.

    An EventHandler maps event categories to handler functions.  These
    functions use the signature 'handler(event, zserv)'.

    .. attribute:: _event_categories_to_handlers
        A dict mapping event categories to handler functions

    Don't use _event_categories_to_handlers directly, instead use
    get_handler() and set_handler()

    """

    def __init__(self):
        """Initializes a BaseEventHandler."""
        zdslog.debug('')
        self._event_categories_to_handlers = dict()
        self.set_handler('error', self.handle_error_event)

    def get_handler(self, event_category):
        """Returns a handler method for a given event_category.

        :param event_category: the category of an event for which to
                               return a handler.
        :type event_category: string
        :rtype: function

        """
        h = self._event_categories_to_handlers.get(event_category,
                                                   self.handle_unhandled_event)
        return h

    def set_handler(self, event_category, handler):
        """Sets the handler method for a certain event_category.

        :param event_category: the category of an event for which to
                               return a handler.
        :type event_category: string
        :param handler: the event handler
        :type handler: a function

        """
        self._event_categories_to_handlers[event_category] = handler

    def handle_error_event(self, event, zserv=None):
        """Handles an error event.

        :param event: the error event
        :type event: :class:`~ZDStack.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ`
        :type zserv: :class:`~ZDStack.ZServ`

        """
        ###
        # Should we really raise an exception here?  I think the rest of the
        # code doesn't assume that event handling stops on an error, so we
        # should at least correct that inconsistency.
        ###
        ###
        # Nah.
        #
        # raise Exception(event.data['error'])
        #
        ###
        zdslog.error("Event error: %s" % (event.data['error']))
        zdslog.error("Event traceback: \n%s\n" % (event.data['traceback']))

    def handle_unhandled_event(self, event, zserv):
        """Handles an unhandled event.

        :param event: the unhandled event
        :type event: LogEvent
        :param zserv: the event's generating ZServ
        :type zserv: ZServ

        """
        pass # do nothing... actually do not handle the event

class ZServEventHandler(BaseEventHandler):

    def __init__(self):
        """Initializes a ZServEventHandler."""
        BaseEventHandler.__init__(self)
        self.set_handler('frag', self.handle_frag_event)
        self.set_handler('join', self.handle_game_join_event)
        self.set_handler('connection', self._sync_players)
        self.set_handler('flag', self.handle_flag_event)
        self.set_handler('death', self.handle_frag_event)
        self.set_handler('rcon', self.handle_rcon_event)
        self.set_handler('command', self.handle_map_change_event)

        ###
        # Old type-based handler stuff
        #
        # self.set_handler('connection', self._sync_players)
        # self.set_handler('disconnection', self._sync_players)
        # self.set_handler('player_lookup', self._sync_players)
        # self.set_handler('game_join', self.handle_game_join_event)
        # self.set_handler('team_join', self.handle_game_join_event)
        # self.set_handler('team_switch', self.handle_game_join_event)
        # self.set_handler('rcon_denied', self.handle_rcon_event)
        # self.set_handler('rcon_granted', self.handle_rcon_event)
        # self.set_handler('rcon_action', self.handle_rcon_event)
        # self.set_handler('flag_touch', self.handle_flag_event)
        # self.set_handler('flag_pick', self.handle_flag_event)
        # self.set_handler('flag_cap', self.handle_flag_event)
        # self.set_handler('flag_loss', self.handle_flag_event)
        # self.set_handler('flag_return', self.handle_flag_return_event)
        # self.set_handler('map_change', self.handle_map_change_event)
        # self.set_handler('frag', self.handle_frag_event)
        # self.set_handler('death', self.handle_frag_event)
        #
        ###

    def _sync_players(self, event, zserv):
        """Syncs players.

        :param event: an event indicating that players should be sync'd
        :type event: LogEvent
        :param zserv: the event's generating ZServ
        :type zserv: ZServ

        """
        zdslog.debug("_sync_players(%s)" % (event))
        if event.type == 'connection':
            ###
            # A 'connection' event has no player name, only an IP address and a
            # port.  So in order to be meaningful, we must wait until the zserv
            # process assigns that connection a name.  This happens with
            # game_join, team_join, and player_lookup events.
            ###
            return
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

        :param event: the game_join event
        :type event: LogEvent
        :param zserv: the event's generating ZServ
        :type zserv: ZServ

        """
        zdslog.debug("handle_game_join_event(%s)" % (event))
        if event.type == 'team_switch':
            ###
            # Team Switches oftentimes occur before player lookup events,
            # and to make matters worse, the player probably hasn't shown up
            # in the zserv's player's list yet.  So we have to sync, with a
            # wait.
            ###
            zserv.players.sync(sleep=TICK)
        try:
            player = zserv.players.get(event.data['player'])
        except PlayerNotFoundError:
            if event.type[0] in 'aeiou':
                es = "Received an %s event for non-existent player [%s]"
            else:
                es = "Received a %s event for non-existent player [%s]"
            zdslog.error(es % (event.type, event.data['player']))
            return
        if event.type in ('team_join', 'team_switch'):
            color = event.data['team']
            with zserv.players.lock:
                player.color = color
                if event.type == 'team_join':
                    ###
                    # You probably can't join a non-playing team, but then
                    # just to be on the safe side:
                    ###
                    player.playing = color in zserv.playing_colors
                else:
                    ###
                    # You can switch from team to team without ever actually
                    # joining the game.  So if the event is a team_switch, the
                    # player is only playing if they were previously playing
                    # AND they've switched to a playing team.
                    ###
                    player.playing = player.playing and \
                                         color in zserv.playing_colors
        else:
            with zserv.players.lock:
                player.playing = True

    def handle_rcon_event(self, event, zserv):
        """Handles an RCON-related event.

        :param event: the rcon event
        :type event: LogEvent
        :param zserv: the event's generating ZServ
        :type zserv: ZServ

        """
        if event.type not in ('rcon_denied', 'rcon_granted', 'rcon_action'):
            es = 'handle_rcon_event does not handle events of type [%s]'
            raise Exception(es % (event.type))
        zdslog.debug('handle_rcon_event(%s)' % (event))
        try:
            player = zserv.players.get(event.data['player'])
        except PlayerNotFoundError:
            es = 'Received an RCON event for non-existent player [%s]'
            zdslog.error(es % (event.data['player']))
            return
        with global_session() as session:
            alias = get_alias(player.name, player.ip,
                              round=zserv.get_round(session=session),
                              session=session)
            if event.type == 'rcon_denied':
                s = RCONDenial(player=alias,
                               round=zserv.get_round(session=session),
                               timestamp=event.dt)
            elif event.type == 'rcon_granted':
                s = RCONAccess(player=alias,
                               round=zserv.get_round(session=session),
                               timestamp=event.dt)
            elif event.type == 'rcon_action':
                s = RCONAction(player=alias,
                               round=zserv.get_round(session=session),
                               timestamp=event.dt, action=event.data['action'])
            persist(s, session=session)

    def handle_flag_event(self, event, zserv):
        """Handles a flag_touch event.

        :param event: the flag event
        :type event: LogEvent
        :param zserv: the event's generating ZServ
        :type zserv: ZServ

        """
        zdslog.debug("handle_flag_event(%s)" % (event))
        if event.type == 'auto_flag_return':
            ###
            # Nothing really to be done here.
            ###
            return
        try:
            player = zserv.players.get(event.data['player'])
        except PlayerNotFoundError:
            es = "Received a flag touch event for non-existent player [%s]"
            zdslog.error(es % (event.data['player']))
            return
        zdslog.debug("Getting state_lock")
        with zserv.state_lock:
            zdslog.debug("Getting state")
            red_holding_flag = 'red' in zserv.teams_holding_flags
            blue_holding_flag = 'blue' in zserv.teams_holding_flags
            green_holding_flag = 'green' in zserv.teams_holding_flags
            white_holding_flag = 'white' in zserv.teams_holding_flags
            red_score = zserv.team_scores.get('red', None)
            blue_score = zserv.team_scores.get('blue', None)
            green_score = zserv.team_scores.get('green', None)
            white_score = zserv.team_scores.get('white', None)
            if event.type in ('flag_touch', 'flag_pick'):
                update = False
                if player not in zserv.players_holding_flags:
                    zserv.players_holding_flags.add(player)
                if player.color not in zserv.teams_holding_flags:
                    zserv.teams_holding_flags.add(player.color)
                s = "Teams holding flags: %s"
                zdslog.debug(s % (str(zserv.teams_holding_flags)))
                zdslog.debug("Getting global session")
                with global_session() as session:
                    alias = get_alias(player.name, player.ip,
                                      round=zserv.get_round(session=session),
                                      session=session)
                    team_color = get_team_color(player.color, session=session)
                    s = FlagTouch(player=alias,
                                  round=zserv.get_round(session=session),
                                  touch_time=event.dt,
                                  was_picked=event.type=='flag_pick',
                                  player_team_color=team_color,
                                  red_team_holding_flag=red_holding_flag,
                                  blue_team_holding_flag=blue_holding_flag,
                                  green_team_holding_flag=green_holding_flag,
                                  white_team_holding_flag=white_holding_flag,
                                  red_team_score=red_score,
                                  blue_team_score=blue_score,
                                  green_team_score=green_score,
                                  white_team_score=white_score)
                    persist(s, session=session)
            elif event.type in ('flag_cap', 'flag_loss'):
                with global_session() as session:
                    try:
                        zdslog.debug("Player Name: [%s]" % (player.name))
                        zdslog.debug("Round ID: [%s]" % (zserv.round_id))
                        q = session.query(FlagTouch)
                        q = q.filter(Alias.name==player.name)
                        q = q.filter(Round.id==zserv.round_id)
                        q = q.order_by(desc(FlagTouch.touch_time))
                        s = q.first()
                        if not s:
                            zdslog.debug("q.first() returned %s" % (s))
                            es = "No FlagTouch by %s found"
                            raise Exception(es % (player.name))
                    except NoResultFound:
                        es = "No FlagTouch by %s found"
                        raise Exception(es % (player.name))
                    s.loss_time = event.dt
                    ds = "Teams holding flags: %s"
                    zdslog.debug(ds % (str(zserv.teams_holding_flags)))
                    zserv.teams_holding_flags.remove(player.color)
                    zserv.players_holding_flags.remove(player)
                    if event.type == 'flag_cap':
                        s.resulted_in_score = True
                        zserv.team_scores[player.color] += 1
                    else: # flag_loss!
                        s.resulted_in_score = False
                        zserv.fragged_runners.append(player)
                    persist(s, update=True, session=session)
            elif event.type == 'flag_return':
                player_holding_flag = player in zserv.players_holding_flags
                red_holding_flag = 'red' in zserv.teams_holding_flags
                blue_holding_flag = 'blue' in zserv.teams_holding_flags
                green_holding_flag = 'green' in zserv.teams_holding_flags
                white_holding_flag = 'white' in zserv.teams_holding_flags
                red_score = zserv.team_scores.get('red', None)
                blue_score = zserv.team_scores.get('blue', None)
                green_score = zserv.team_scores.get('green', None)
                white_score = zserv.team_scores.get('white', None)
                with global_session() as session:
                    round = zserv.get_round(session=session)
                    alias = get_alias(player.name, player.ip,
                                      round=round, session=session)
                    team_color = get_team_color(player.color, session=session)
                    s = FlagReturn(player=alias, round=round,
                                   timestamp=event.dt,
                                   player_was_holding_flag=player_holding_flag,
                                   player_team_color=team_color,
                                   red_team_holding_flag=red_holding_flag,
                                   blue_team_holding_flag=blue_holding_flag,
                                   green_team_holding_flag=green_holding_flag,
                                   white_team_holding_flag=white_holding_flag,
                                   red_team_score=red_score,
                                   blue_team_score=blue_score,
                                   green_team_score=green_score,
                                   white_team_score=white_score)
                    persist(s, session=session)

    def handle_frag_event(self, event, zserv):
        """Handles a frag event.

        :param event: the frag event
        :type event: LogEvent
        :param zserv: the event's generating ZServ
        :type zserv: ZServ

        """
        zdslog.debug("handle_frag_event(%s)" % (event))
        with zserv.state_lock:
            try:
                fraggee = zserv.players.get(event.data['fraggee'])
            except PlayerNotFoundError:
                es = "Received a death event for non-existent player [%s]"
                zdslog.error(es % (event.data['fraggee']))
                return
            if 'fragger' in event.data:
                try:
                    fragger = zserv.players.get(event.data['fragger'])
                except PlayerNotFoundError:
                    es = "Received a frag event for non-existent player [%s]"
                    zdslog.error(es % (event.data['fragger']))
                    return
                is_suicide = False
            else:
                fragger = fraggee
                is_suicide = True
            if fraggee in zserv.fragged_runners:
                fraggee_was_holding_flag = True
                zserv.fragged_runners.remove(fraggee)
            else:
                fraggee_was_holding_flag = False
            if is_suicide:
                fragger_was_holding_flag = fraggee_was_holding_flag
            else:
                fragger_was_holding_flag = \
                    fragger in zserv.players_holding_flags
            if zserv.game_mode in TEAMDM_MODES:
                if is_suicide:
                    zserv.team_scores[fragger.color] -= 1
                else:
                    zserv.team_scores[fragger.color] += 1
            red_holding_flag = False
            blue_holding_flag = False
            green_holding_flag = False
            white_holding_flag = False
            ###
            # Because the flag-loss happens before the frag, we have to lookup
            # the fraggee's team and ensure it's set as a team that was holding
            # a flag at the time of the frag.  For the other teams we can just
            # look them up.
            ###
            if (fraggee_was_holding_flag and fraggee.color == 'red') or \
               'red' in zserv.teams_holding_flags:
                red_holding_flag = True
            if (fraggee_was_holding_flag and fraggee.color == 'blue') or \
               'blue' in zserv.teams_holding_flags:
                blue_holding_flag = True
            if (fraggee_was_holding_flag and fraggee.color == 'green') or \
               'green' in zserv.teams_holding_flags:
                green_holding_flag = True
            if (fraggee_was_holding_flag and fraggee.color == 'white') or \
               'white' in zserv.teams_holding_flags:
                white_holding_flag = True
            red_score = zserv.team_scores.get('red', None)
            blue_score = zserv.team_scores.get('blue', None)
            green_score = zserv.team_scores.get('green', None)
            white_score = zserv.team_scores.get('white', None)
            with global_session() as session:
                fragger_team_color = None
                fraggee_team_color = None
                if zserv.game_mode in TEAM_MODES:
                    fraggee_team_color = get_team_color(color=fraggee.color,
                                                        session=session)
                    if is_suicide:
                        fragger_team_color = fraggee_team_color
                    else:
                        fragger_team_color = get_team_color(color=fragger.color,
                                                            session=session)
                weapon = get_weapon(name=event.data['weapon'],
                                    is_suicide=is_suicide, session=session)
                zdslog.debug("Getting ZServ's round")
                round = zserv.get_round(session=session)
                zdslog.debug("Getting Fraggee Alias")
                fraggee_alias = get_alias(fraggee.name, fraggee.ip,
                                          round=round, session=session)
                if fraggee == fragger:
                    fragger_alias = fraggee_alias
                else:
                    zdslog.debug("Getting Fragger Alias")
                    fragger_alias = get_alias(fragger.name, fragger.ip,
                                              round=round, session=session)
                zdslog.debug("Getting Frag")
                s = Frag(fragger=fragger_alias, fraggee=fraggee_alias,
                         weapon=weapon, round=round, timestamp=event.dt,
                         fragger_was_holding_flag=fragger_was_holding_flag,
                         fraggee_was_holding_flag=fraggee_was_holding_flag,
                         fragger_team_color=fragger_team_color,
                         fraggee_team_color=fraggee_team_color,
                         red_team_holding_flag=red_holding_flag,
                         blue_team_holding_flag=blue_holding_flag,
                         green_team_holding_flag=green_holding_flag,
                         white_team_holding_flag=white_holding_flag,
                         red_team_score=red_score,
                         blue_team_score=blue_score,
                         green_team_score=green_score,
                         white_team_score=white_score)
                zdslog.debug("Persisting Frag")
                persist(s, session=session)
                zdslog.debug("Done!")

    def handle_map_change_event(self, event, zserv):
        """Handles a map_change event.

        :param event: the map_change event
        :type event: LogEvent
        :param zserv: the event's generating ZServ
        :type zserv: ZServ

        """
        if not event.type == 'map_change':
            return
        zdslog.debug("handle_map_change_event(%s)" % (event))
        zserv.change_map(event.data['number'], event.data['name'])

