from __future__ import with_statement

import datetime

from sqlalchemy import and_

from ZDStack import TICK, PlayerNotFoundError, get_session_class, get_zdslog
from ZDStack.ZServ import TEAM_MODES, TEAMDM_MODES
from ZDStack.ZDSModels import Weapon, Round, Alias, Frag, FlagTouch, \
                              FlagReturn, RCONAccess, RCONDenial, RCONAction, \
                              GameMode, TeamColor
from ZDStack.ZDSDatabase import requires_session

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

class ManualEventHandler(BaseEventHandler):

    def __init__(self, map_id):
        BaseEventHandler.__init__(self)
        self.map_id = map_id
        self._weapons = dict()
        self._team_colors = dict()
        self._current_round = None
        self._aliases = dict()
        self._players_holding_flags = set()
        self._teams_holding_flags = set()
        self._fragged_runners = set()
        self._team_scores = dict(red=0, blue=0)
        self.set_handler('join', self.handle_join_event)       # game_join
        self.set_handler('frag', self.handle_frag_event)       # 
        self.set_handler('death', self.handle_frag_event)      # 
        self.set_handler('flag', self.handle_flag_event)       # 
        self.set_handler('rcon', self.handle_rcon_event)       # 
        self.set_handler('command', self.handle_command_event) # map_change

    def reset(self):
        self._weapons.clear()
        self._team_colors.clear()
        self._current_round = None
        self._aliases.clear()
        self._players_holding_flags.clear()
        self._teams_holding_flags.clear()
        self._fragged_runners.clear()
        self._team_scores['red'] = 0
        self._team_scores['blue'] = 0

    @property
    def round_id(self):
        if self._current_round:
            return self._current_round.id
        raise Exception(
            "Cannot get current round's ID when there is no current round"
        )

    @requires_session
    def setup_new_round(self, start_time, session=None):
        zdslog.debug("get_new_round")
        r = Round()
        ctf = session.query(GameMode).get('ctf')
        r.game_mode_name = 'ctf'
        r.game_mode = ctf
        r.map_id = self.map_id
        r.start_time = start_time
        session.merge(ctf)
        session.add(r)
        zdslog.info('Created new round %r' % (r))
        self._current_round = r

    @requires_session
    def get_alias(self, name, session=None):
        zdslog.debug("get_alias")
        if name not in self._aliases:
            alias = session.query(Alias).filter(Alias.name==name).first()
            if not alias:
                alias = Alias()
                alias.name = name
                alias.ip_address = '255.255.255.255'
                zdslog.debug("Persisting %s" % (alias))
                session.add(alias)
            self._aliases[name] = alias
        zdslog.debug("Alias.id: %s" % (self._aliases[name].id))
        return self._aliases[name]

    @requires_session
    def get_weapon(self, name, session=None):
        zdslog.debug("get_weapon")
        if name not in self._weapons:
            self._weapons[name] = session.query(Weapon).get(name)
        return self._weapons[name]

    @requires_session
    def get_team_color(self, color, session=None):
        zdslog.debug("get_team_color")
        if color not in self._team_colors:
            zdslog.debug("%s not in %s" % (color, self._team_colors))
            try:
                team_color = session.query(TeamColor).get(color)
            except NoResultFound:
                team_color = TeamColor()
                team_color.color = color
                zdslog.debug("Persisting %s" % (team_color))
                session.add(team_color)
            self._team_colors[color] = team_color
        return self._team_colors[color]

    def add_runner(self, runner):
        self._players_holding_flags.add(runner)
        self._teams_holding_flags.add(runner.color.lower())

    def remove_runner(self, runner):
        self._players_holding_flags.remove(runner)
        self._teams_holding_flags.remove(runner.color.lower())

    @requires_session
    def _add_common_state(self, event, stat, player_holding_flag,
                                player_color, session=None):
        stat.round = self._current_round
        stat.red_team_score = self._team_scores.get('red', None)
        stat.blue_team_score = self._team_scores.get('blue', None)
        stat.green_team_score = self._team_scores.get('green', None)
        stat.white_team_score = self._team_scores.get('white', None)
        stat.red_holding_flag = False
        stat.blue_holding_flag = False
        stat.green_holding_flag = False
        stat.white_holding_flag = False
        if (player_holding_flag and player_color == 'red') or \
            'red' in self._teams_holding_flags:
            stat.red_holding_flag = True
        if (player_holding_flag and player_color == 'blue') or \
            'blue' in self._teams_holding_flags:
            stat.blue_holding_flag = True
        if (player_holding_flag and player_color == 'green') or \
            'green' in self._teams_holding_flags:
            stat.green_holding_flag = True
        if (player_holding_flag and player_color == 'white') or \
            'white' in self._teams_holding_flags:
            stat.white_holding_flag = True

    @requires_session
    def handle_frag_event(self, event, session=None):
        zdslog.debug("handle_frag_event")
        weapon = self.get_weapon(event.data['weapon'], session=session)
        frag = Frag()
        frag.timestamp = event.dt
        frag.weapon = weapon
        frag.fraggee = self.get_alias(event.data['fraggee'], session=session)
        frag.fraggee_team_color = self.get_team_color(
            frag.fraggee.color,
            session=session
        )
        if frag.fraggee in self._fragged_runners:
            frag.fraggee_was_holding_flag = True
            self._fragged_runners.remove(frag.fraggee)
        else:
            frag.fraggee_was_holding_flag = False
        self._add_common_state(
            event,
            frag,
            frag.fraggee_was_holding_flag,
            frag.fraggee_team_color.color,
            session=session
        )
        if 'fragger' in event.data:
            frag.is_suicide = False
            frag.fragger = self.get_alias(
                event.data['fragger'],
                session=session
            )
            frag.fragger_team_color = self.get_team_color(
                frag.fragger.color,
                session=session
            )
            if frag.fragger in self._players_holding_flags:
                frag.fragger_was_holding_flag = True
            else:
                frag.fragger_was_holding_flag = False
        else:
            frag.is_suicide = True
            frag.fragger = frag.fraggee
            frag.fragger_team_color = frag.fraggee_team_color
            frag.fragger_was_holding_flag = frag.fraggee_was_holding_flag
        zdslog.debug("Fragger holding flag: %s" % (frag.fragger_was_holding_flag))
        zdslog.debug("Fraggee holding flag: %s" % (frag.fraggee_was_holding_flag))
        session.add(frag)
        ###
        # session.merge(weapon)
        # session.merge(fraggee)
        # session.merge(self._current_round)
        # if not frag.is_suicide:
        #     session.merge(fragger)
        # session.add(frag)
        ###

    @requires_session
    def handle_flag_event(self, event, session=None):
        zdslog.debug("handle_flag_event")
        ###
        # flag_return
        # flag_touch
        # flag_cap
        # flag_loss
        ###
        if event.type == 'auto_flag_return':
            # Nothing we can do here
            return
        alias = self.get_alias(event.data['player'], session=session)
        if event.type in ('flag_return', 'flag_touch', 'flag_pick'):
            if event.type == 'flag_return':
                stat = FlagReturn()
                stat.timestamp = event.dt
                stat.player_holding_flag = alias in self._players_holding_flags
                player_holding_flag = True
            elif event.type in ('flag_touch', 'flag_pick'):
                stat = FlagTouch()
                stat.touch_time = event.dt
                stat.loss_time = None
                stat.was_picked = event.type == 'flag_pick'
                stat.resulted_in_score = None
                player_holding_flag = False
            stat.alias = alias
            stat.player_team_color = self.get_team_color(
                alias.color,
                session=session
            )
            self._add_common_state(
                event,
                stat,
                player_holding_flag,
                stat.player_team_color.color,
                session=session
            )
            if event.type in ('flag_touch', 'flag_pick'):
                self.add_runner(alias)
            zdslog.debug("Persisting %s" % (stat))
            zdslog.debug('Recording flag touch/pick by %s in round %s' % (
                alias.id, self._current_round.id
            ))
            session.add(stat)
        elif event.type in ('flag_cap', 'flag_loss'):
            self.remove_runner(alias)
            q = session.query(FlagTouch)
            q = q.filter(and_(
                FlagTouch.player_id==alias.id,
                FlagTouch.round_id==self._current_round.id,
            ))
            stat = q.order_by(FlagTouch.touch_time.desc()).first()
            if not stat:
                raise Exception('No flag touch by %s in round %s recorded' % (
                    alias.id, self._current_round.id
                ))
            stat.loss_time = event.dt
            if event.type == 'flag_cap':
                stat.resulted_in_score = True
                self._team_scores[stat.player_team_color_name] += 1
            else:
                stat.resulted_in_score = False
                self._fragged_runners.add(alias)
            zdslog.debug("Updating %s" % (stat))
            session.merge(stat)

    @requires_session
    def handle_join_event(self, event, session=None):
        zdslog.debug("handle_join_event")
        alias = self.get_alias(event.data['player'], session=session)
        alias.color = event.data['team'].lower()
        if event.type == 'team_join':
            self._current_round.aliases.append(alias)
            zdslog.debug("Updating %s" % (alias))
            session.merge(self._current_round)

    @requires_session
    def handle_command_event(self, event, session=None):
        zdslog.debug("handle_command_event")
        if event.type == 'map_change':
            if self._current_round is not None:
                self._current_round.end_time = event.dt
                session.merge(self._current_round)
            self.reset()
            self.setup_new_round(event.dt, session=session)

    def handle_connection_event(self, event):
        pass

    def handle_rcon_event(self, event):
        pass


class ZServEventHandler(BaseEventHandler):

    def __init__(self):
        """Initializes a ZServEventHandler."""
        BaseEventHandler.__init__(self)
        self.set_handler('frag', self.handle_frag_event)
        self.set_handler('join', self.handle_game_join_event)
        self.set_handler('connection', self.handle_connection_event)
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

    @requires_session
    def _get_alias(self, event, key, zserv, acquire_lock=True, session=None):
        try:
            return zserv.players.get(event.data[key], session=session,
                                     acquire_lock=False)
        except PlayerNotFoundError:
            if event.type[0] in 'aeiou':
                es = "Received an %s event for non-existent player [%s]"
            else:
                es = "Received a %s event for non-existent player [%s]"
            zdslog.error(es % (event.type.replace('_', ' '), event.data[key]))

    @requires_session
    def _add_common_state(self, model, event, zserv, session=None):
        """Adds common state information to a model.

        :param model: an instance of a model, i.e. FlagTouch
        :param event: the time at which the event occurred
        :type event: :class:`ZDStack.LogEvent.LogEvent`
        :param zserv: the originating ZServ
        :type zserv: :class:`~ZDStack.ZDStack.ZServ`
        :param session: a database session
        :type session: SQLAlchemy Session

        """
        zdslog.debug("Adding common state to %s" % (model))
        model.round_id = zserv.round_id
        model.round = zserv.get_round(session=session)
        zdslog.debug("Event category is %s" % (event.category))
        zdslog.debug("Event type is %s" % (event.type))
        if event.category in ('frag', 'death'):
            zdslog.debug("Handling a frag/death event")
            fraggee = self._get_alias(event, 'fraggee', zserv, session=session)
            if not fraggee:
                zdslog.debug("Couldn't find fraggee")
                return
            ###
            fraggee_color = fraggee.color
            model.fraggee_team_color_name = fraggee_color
            if fraggee_color:
                fraggee_color = fraggee_color.lower()
                # model.fraggee_team_color = \
                #                     zserv.team_color_instances[fraggee_color]
            ###
            model.fraggee = fraggee
            model.fraggee_id = fraggee.id
            if fraggee in zserv.fragged_runners:
                model.fraggee_was_holding_flag = True
                zserv.fragged_runners.remove(fraggee)
            else:
                model.fraggee_was_holding_flag = False
            if 'fragger' in event.data:
                fragger = self._get_alias(event, 'fragger', zserv,
                                          session=session)
                if not fragger:
                    zdslog.debug("Could find fraggee")
                    return
                model.is_suicide = False
                ###
                fragger_color = fragger.color
                model.fragger_team_color_name = fragger_color
                if fragger_color:
                    fragger_color = fragger_color.lower()
                    # model.fragger_team_color = \
                    #                 zserv.team_color_instances[fragger_color]
                    if zserv.game_mode in TEAMDM_MODES:
                        zserv.team_scores[fragger_color] += 1
                ###
                model.fragger = fragger
                model.fragger_id = fragger.id
                model.fragger_was_holding_flag = \
                                        fragger in zserv.players_holding_flags
            else:
                model.is_suicide = True
                model.fragger_team_color_name = fraggee_color
                model.fragger_was_holding_flag = model.fraggee_was_holding_flag
                if fraggee_color and zserv.game_mode in TEAMDM_MODES:
                    zserv.team_scores[fraggee_color] -= 1
        elif event.category == 'rcon' or event.type in (
            'flag_pick',
            'flag_touch',
            'flag_return'
        ):
            zdslog.debug("Handling an rcon or flag event")
            alias = self._get_alias(event, 'player', zserv, session=session)
            if not alias:
                return
            model.alias = alias
            model.player_id = alias.id
            if event.type in ('flag_touch', 'flag_pick', 'flag_return'):
                color = alias.color.lower()
                model.player_team_color_name = color
                # model.player_team_color = zserv.team_color_instances[color]
                if event.type == 'flag_return':
                    model.player_was_holding_flag = \
                                        alias in zserv.players_holding_flags
                    ds = 'Flag Return, players holding flags: %s'
                    zdslog.debug(ds % (zserv.players_holding_flags))
                else:
                    ds = 'Flag Touch/Pick 1, players holding flags: %s'
                    zdslog.debug(ds % (zserv.players_holding_flags))
                    zserv.players_holding_flags.add(alias)
                    zserv.teams_holding_flags.add(alias.color.lower())
                    model.was_picked = event.type == 'flag_pick'
                    ds = 'Flag Touch/Pick 2, players holding flags: %s'
                    zdslog.debug(ds % (zserv.players_holding_flags))
            if event.type == 'rcon_action':
                model.action = event.data['action']
        else:
            zdslog.debug("Handling some other kind of event: %r" % (event))
        if event.type not in ('flag_touch', 'flag_pick'):
            zdslog.debug("Setting timestamp of %s to %s" % (model, event.dt))
            model.timestamp = event.dt
        else:
            zdslog.debug("Not setting timestamp of %s" % (model))
        if event.category in ('frag', 'death') or \
           event.type in ('flag_pick', 'flag_touch', 'flag_return'):
            model.red_team_holding_flag = 'red' in zserv.teams_holding_flags
            model.blue_team_holding_flag = 'blue' in zserv.teams_holding_flags
            model.green_team_holding_flag = 'green' in zserv.teams_holding_flags
            model.white_team_holding_flag = 'white' in zserv.teams_holding_flags
            if event.category in ('frag', 'death'):
                try:
                    q = session.query(Weapon)
                    weapon = q.filter_by(name=event.data['weapon']).one()
                except NoResultFound:
                    weapon = Weapon()
                    weapon.name = event.data['weapon']
                    if event.category == 'death' or model.is_suicide:
                        weapon.is_suicide = True
                    else:
                        weapon.is_suicide = False
                    session.add(weapon)
                model.weapon_name = weapon.name
                model.weapon = weapon
                if model.fraggee_was_holding_flag:
                    ###
                    # Because the flag-loss happens before the frag, we have
                    # to lookup the fraggee's team and ensure it's set as a
                    # team that was holding a flag at the time of the frag.
                    # For the other teams we can just look them up.
                    ###
                    if fraggee_color == 'red':
                        model.red_holding_flag = True
                    elif fraggee_color == 'blue':
                        model.blue_holding_flag = True
                    elif fraggee_color == 'green':
                        model.green_holding_flag = True
                    elif fraggee_color == 'white':
                        model.white_holding_flag = True
            model.red_team_score = zserv.team_scores.get('red', None)
            model.blue_team_score = zserv.team_scores.get('blue', None)
            model.green_team_score = zserv.team_scores.get('green', None)
            model.white_team_score = zserv.team_scores.get('white', None)
        return model

    @requires_session
    def handle_connection_event(self, event, zserv, session=None):
        """Handles a connection event.

        :param event: an event indicating that players should be sync'd
        :type event: :class:`~ZDStack.LogEvent.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :param session: a database session
        :type session: SQLAlchemy Session

        """
        zdslog.debug("_sync_players(%s)" % (event))
        ###
        # Handled event types:
        #
        #   - connection    (xxx.xxx.xxx.xxx:30666 connection (v. 108)
        #   - disconnection (> xxxxxx disconnected)
        #   - player_lookup (> xxxxxx has connected.)
        #
        # It's not useful to do anything upon receipt of a 'connection' event,
        # because the zserv hasn't associated a player name with it yet.
        # However, the other two events require a player sync.
        #
        ###
        if event.type in ('disconnection', 'player_lookup'):
            zserv.players.sync(check_bans=True, session=session)

    @requires_session
    def handle_game_join_event(self, event, zserv, session=None):
        """Handles a game_join event.

        :param event: the game_join event
        :type event: :class:`~ZDStack.LogEvent.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :param session: a database session
        :type session: SQLAlchemy Session

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
        # ------------------------------------------------------------
        # | CATEGORY   | TYPE          | HANDLER FUNCTION            |
        # |------------|---------------|-----------------------------|
        # | connection | connection    | unhandled                   |
        # |------------|---------------|-----------------------------|
        # | join       | team_switch   | self.handle_game_join_event |
        # |------------|---------------|-----------------------------|
        # | connection | player_lookup | self._sync_players          |
        # ------------------------------------------------------------
        #
        ###
        zdslog.debug("Acquiring %s" % (zserv.players.lock))
        with zserv.players.lock:
            zdslog.debug("Acquired %s" % (zserv.players.lock))
            if event.type == 'team_switch':
                zserv.players.sync(check_bans=True, acquire_lock=False,
                                   session=session)
            player = self._get_alias(event, 'player', zserv, session=session,
                                     acquire_lock=False)
            if not player:
                return
            if 'team' in event.data:
                color = event.data['team'].lower()
            if event.type in ('team_join', 'team_switch'):
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
                player.playing = True
            round = zserv.get_round(session=session)
            if player.playing and not player in round.aliases:
                round.aliases.append(player)
            session.merge(player)
            session.merge(round)
        zdslog.debug("Released %s" % (zserv.players.lock))

    @requires_session
    def handle_rcon_event(self, event, zserv, session=None):
        """Handles an RCON-related event.

        :param event: the RCON event
        :type event: :class:`~ZDStack.LogEvent.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :param session: a database session
        :type session: SQLAlchemy Session

        """
        zdslog.debug('handle_rcon_event(%s)' % (event))
        if event.type == 'rcon_denied':
            s = RCONDenial()
        elif event.type == 'rcon_granted':
            s = RCONAccess()
        elif event.type == 'rcon_action':
            s = RCONAction()
        zdslog.debug("Acquiring %s" % (zserv.state_lock))
        with zserv.state_lock:
            zdslog.debug("Acquired %s" % (zserv.state_lock))
            zdslog.debug("Persisting [%s]" % (s))
            s = self._add_common_state(s, event, zserv, session=session)
            session.add(s)
            zdslog.debug("Released %s" % (zserv.state_lock))

    @requires_session
    def handle_flag_event(self, event, zserv, session=None):
        """Handles a flag_touch event.

        :param event: the flag event
        :type event: :class:`~ZDStack.LogEvent.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :param session: a database session
        :type session: SQLAlchemy Session

        """
        zdslog.debug("handle_flag_event(%s)" % (event))
        if event.type == 'auto_flag_return':
            ###
            # Nothing really to be done here.
            ###
            return
        zdslog.debug("Acquiring %s" % (zserv.state_lock))
        with zserv.state_lock:
            zdslog.debug("Acquired %s" % (zserv.state_lock))
            if event.type in ('flag_cap', 'flag_loss'):
                player = self._get_alias(event, 'player', zserv,
                                         session=session)
                q = session.query(FlagTouch)
                q = q.filter(and_(FlagTouch.player_id==player.id,
                                  FlagTouch.round_id==zserv.round_id))
                stat = q.order_by(FlagTouch.touch_time.desc()).first()
                if not stat:
                    es = "Couldn't find FlagTouch by %s in %d"
                    zdslog.error(es % (player.name, zserv.round_id))
                    return
                player = self._get_alias(event, 'player', zserv,
                                         session=session)
                stat.loss_time = event.dt
                try:
                    zserv.players_holding_flags.remove(player)
                except KeyError:
                    ds = "%s not in %s"
                    zdslog.error(ds % (player, zserv.players_holding_flags))
                try:
                    zserv.teams_holding_flags.remove(player.color.lower())
                except KeyError:
                    ds = "%s not in %s"
                    zdslog.error(ds % (player.color.lower(),
                                       zserv.teams_holding_flags))
                if event.type == 'flag_cap':
                    stat.resulted_in_score = True
                    color = player.color.lower()
                    ds = "Player team score: %d"
                    zdslog.debug(ds % (zserv.team_scores[color]))
                    zserv.team_scores[color] += 1
                else:
                    stat.resulted_in_score = False
                    zserv.fragged_runners.append(player)
                zdslog.debug("Updating [%s]" % (stat))
                session.merge(stat)
            elif event.type in ('flag_touch', 'flag_pick', 'flag_return'):
                if event.type == 'flag_return':
                    stat = FlagReturn()
                else:
                    stat = FlagTouch()
                stat = self._add_common_state(stat, event, zserv,
                                              session=session)
                zdslog.debug("Persisting[%s]" % (stat))
                session.add(stat)
            else:
                zdslog.error("Unsupported event type: [%s]" % (event.type))
        zdslog.debug("Released %s" % (zserv.state_lock))

    @requires_session
    def handle_frag_event(self, event, zserv, session=None):
        """Handles a frag event.

        :param event: the frag event
        :type event: :class:`~ZDStack.LogEvent.LogEvent`
        :param zserv: the event's generating :class:`~ZDStack.ZServ.ZServ`
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :param session: a database session
        :type session: SQLAlchemy Session

        """
        zdslog.debug("handle_frag_event(%s)" % (event))
        zdslog.debug("Acquiring %s" % (zserv.state_lock))
        with zserv.state_lock:
            zdslog.debug("Acquired %s" % (zserv.state_lock))
            zdslog.debug("Persisting Frag")
            frag = self._add_common_state(Frag(), event, zserv, session=session)
            if frag:
                session.add(frag)
            else:
                es = "Something horrible happened in _add_common_state"
                zdslog.error(es)
            zdslog.debug("Done!")
        zdslog.debug("Released %s" % (zserv.state_lock))

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

