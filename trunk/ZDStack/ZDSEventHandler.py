from __future__ import with_statement

import datetime

from ZDStack import TICK, PlayerNotFoundError, get_session_class, get_zdslog
from ZDStack.ZServ import TEAM_MODES, TEAMDM_MODES
from ZDStack.ZDSModels import Weapon, Round, Alias, Frag, FlagTouch, \
                              FlagReturn, RCONAccess, RCONDenial, RCONAction
from ZDStack.ZDSDatabase import global_session, persist

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
        :type event: :class:`~ZDStack.LogEvent.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`

        """
        zdslog.error("Event error: %s" % (event.data['error']))
        zdslog.error("Event traceback: \n%s\n" % (event.data['traceback']))

    def handle_unhandled_event(self, event, zserv=None):
        """Handles an unhandled event.

        :param event: the unhandled event
        :type event: :class:`~ZDStack.LogEvent.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`

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
        :type event: :class:`~ZDStack.LogEvent.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`

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
        zserv.players.sync(check_bans=True)

    def handle_game_join_event(self, event, zserv):
        """Handles a game_join event.

        :param event: the game_join event
        :type event: :class:`~ZDStack.LogEvent.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`

        """
        zdslog.debug("handle_game_join_event(%s)" % (event))
        ###
        # Here's an example of how 1.08.08 logs player connections in CTF:
        #
        # xxx.xxx.xxx.xxx:30666 connection (v. 108)
        # > xxxxxxx is now on the Blue team.
        # > xxxxxxx has connected.
        #
        # These lines map thusly:
        #
        # | connection | connection    | unhandled                   |
        # | join       | team_switch   | self.handle_game_join_event |
        # | connection | player_lookup | self._sync_players          |
        #
        ###
        try:
            ###
            # team_switch events can occur before the player has a name,
            # fortunately players.get() will sync() for us if the player is not
            # initially found.
            ###
            player = zserv.players.get(name=event.data['player'])
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
        with global_session() as session:
            round = zserv.get_round(session=session)
            if player.playing and not round in player.rounds:
                player.rounds.append(round)
            persist(player, update=True, session=session)

    def handle_rcon_event(self, event, zserv):
        """Handles an RCON-related event.

        :param event: the RCON event
        :type event: :class:`~ZDStack.LogEvent.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`

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
            if event.type == 'rcon_denied':
                s = RCONDenial()
            elif event.type == 'rcon_granted':
                s = RCONAccess()
            elif event.type == 'rcon_action':
                s = RCONAction()
                s.action = event.data['action']
            else:
                zdslog.error("Unsupported event type [%s]" % (event.type))
                return
            s.alias = player
            s.timestamp = event.dt
            s.round = zserv.get_round(session=session)
            session.add(s)

    def handle_flag_event(self, event, zserv):
        """Handles a flag_touch event.

        :param event: the flag event
        :type event: :class:`~ZDStack.LogEvent.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`

        """
        zdslog.debug("handle_flag_event(%s)" % (event))
        if event.type == 'auto_flag_return':
            ###
            # Nothing really to be done here.
            ###
            return
        zdslog.debug("Getting state_lock")
        with zserv.state_lock:
            zdslog.debug("Getting global session")
            with global_session as session():
                zdslog.debug("Inside global session")
                try:
                    player = zserv.players.get(event.data['player'])
                except PlayerNotFoundError:
                    es = "Received a flag touch event for non-existent player "
                    es += "[%s]"
                    zdslog.error(es % (event.data['player']))
                    return
            if event.type in ('flag_return', 'flag_touch', 'flag_pick'):
                if event.type == 'flag_return':
                    stat = FlagReturn()
                    stat.timestamp = event.dt
                    stat.player_holding_flag = \
                                        player in zserv.players_holding_flags
                else:
                    stat = FlagTouch()
                    stat.touch_time = event.dt
                    stat.loss_time = None
                    stat.was_picked = event.type == 'flag_pick'
                    zserv.players_holding_flags.add(player)
                    zserv.teams_holding_flags.add(player.color.lower())
                stat.round_id = zserv.round_id
                stat.player_id = player.id
                stat.player_team_color_name = player.color.lower()
                zdslog.debug("Getting state")
                stat.red_holding_flag = 'red' in zserv.teams_holding_flags
                stat.blue_holding_flag = 'blue' in zserv.teams_holding_flags
                stat.green_holding_flag = 'green' in zserv.teams_holding_flags
                stat.white_holding_flag = 'white' in zserv.teams_holding_flags
                stat.red_score = zserv.team_scores.get('red', None)
                stat.blue_score = zserv.team_scores.get('blue', None)
                stat.green_score = zserv.team_scores.get('green', None)
                stat.white_score = zserv.team_scores.get('white', None)
            elif event.type in ('flag_cap', 'flag_loss'):
                q = session.query(FlagTouch)
                q = q.filter(and_(FlagTouch.player_id==player.id,
                                  FlagTouch.round_id==zserv.round_id))
                stat = q.order_by(FlagTouch.touch_time.desc()).first()
                if not stat:
                    es = "Couldn't find FlagTouch by %s in %d"
                    zdslog.error(es % (player.name, zserv.round_id))
                    return
                stat.loss_time = event.dt
                zserv.players_holding_flags.remove(player)
                zserv.teams_holding_flags.remove(alias.color.lower())
                if event.type == 'flag_cap':
                    stat.resulted_in_score = True
                    zserv.team_scores[player.color.lower()] += 1
                else:
                    stat.resulted_in_score = False
                    zserv.fragged_runners.append(alias)
            else:
                zdslog.error("Unsupported event type: [%s]" % (event.type))
                return
            zdslog
            session.add(stat)

    def handle_frag_event(self, event, zserv):
        """Handles a frag event.

        :param event: the frag event
        :type event: :class:`~ZDStack.LogEvent.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`

        """
        zdslog.debug("handle_frag_event(%s)" % (event))
        with zserv.state_lock:
            with global_session() as session:
                try:
                    q = session.query(Weapon)
                    weapon = q.filter_by(name=event.data['weapon']).one()
                except NoResultFound:
                    weapon = Weapon()
                    weapon.name = event.data['weapon']
                    weapon.is_suicide = not 'fragger' in event.data
                    session.add(weapon)
                frag = Frag()
                frag.round_id = zserv.round_id
                frag.timestamp = event.dt
                frag.weapon_name = weapon.name
                try:
                    fraggee = zserv.players.get(name=event.data['fraggee'])
                    frag.fraggee_id = fraggee.id
                    frag.fraggee_team_color_name = fraggee.color
                    if fraggee in zserv.fragged_runners:
                        frag.fraggee_was_holding_flag = True
                        zserv.fragged_runners.remove(fraggee)
                    else:
                        frag.fraggee_was_holding_flag = False
                    if 'fragger' in event.data:
                        fragger = zserv.players.get(name=event.data['fragger'])
                        frag.is_suicide = False
                        frag.fragger_team_color_name = fragger.color
                        frag.fragger_was_holding_flag = \
                                        fragger in zserv.players_holding_flags
                        if zserv.game_mode in TEAMDM_MODES:
                            zserv.team_scores[fragger.color] += 1
                    else:
                        frag.is_suicide = True
                        frag.fragger_team_color_name = fraggee.color
                        frag.fragger_was_holding_flag = \
                                                frag.fraggee_was_holding_flag
                        if zserv.game_mode in TEAMDM_MODES:
                            zserv.team_scores[fragger.color] -= 1
                except PlayerNotFoundError, pnfe:
                    es = "Received a frag event for non-existent player [%s]"
                    zdslog.error(es % (pnfe.name))
                    return
            frag.red_holding_flag = 'red' in zserv.teams_holding_flags
            frag.blue_holding_flag = 'blue' in zserv.teams_holding_flags
            frag.green_holding_flag = 'green' in zserv.teams_holding_flags
            frag.white_holding_flag = 'white' in zserv.teams_holding_flags
            frag.red_score = zserv.team_scores.get('red', None)
            frag.blue_score = zserv.team_scores.get('blue', None)
            frag.green_score = zserv.team_scores.get('green', None)
            frag.white_score = zserv.team_scores.get('white', None)
            ###
            # Because the flag-loss happens before the frag, we have to lookup
            # the fraggee's team and ensure it's set as a team that was holding
            # a flag at the time of the frag.  For the other teams we can just
            # look them up.
            ###
            if frag.fraggee_was_holding_flag:
                if fraggee.color == 'red':
                    frag.red_holding_flag = True
                elif fraggee.color == 'blue':
                    frag.blue_holding_flag = True
                elif fraggee.color == 'green':
                    frag.green_holding_flag = True
                elif fraggee.color == 'white':
                    frag.white_holding_flag = True
                zdslog.debug("Persisting Frag")
                session.add(Frag)
                zdslog.debug("Done!")

    def handle_map_change_event(self, event, zserv):
        """Handles a map_change event.

        :param event: the map_change event
        :type event: :class:`~ZDStack.LogEvent.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`

        """
        if not event.type == 'map_change':
            return
        zdslog.debug("handle_map_change_event(%s)" % (event))
        zserv.change_map(event.data['number'], event.data['name'])

