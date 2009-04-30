################################################################################
#                                                                              #
# Fair Teams ZDStack Plugin                                                    #
#                                                                              #
#   This plugin maintains team fairness by enforcing the following rules:      #
#     - No team can have more than a 1 player advantage at any time            #
#     - Winning teams can not have a player advantage of any size              #
#                                                                              #
#   Players who cause violations of these rules are warned, and subsequently   #
#   kicked if the situation is not resolved.  In the event that players        #
#   disconnecting causes a team imbalance, random players from the advantaged  #
#   team are kicked if the situation is not resolved.  The amount of time      #
#   to offending teams or players is configurable by setting the               #
#   BALANCE_WINDOW variable here.                                              #
#                                                                              #
################################################################################

from __future__ import with_statement

from threading import Timer
from ZDStack import TEAM_COLORS, PlayerNotFoundError
from ZDStack.ZServ import TEAM_MODES

BALANCE_WINDOW = 15 # 15 seconds

###
# Because we've already acquired the ZServ's event lock, we don't separate
# locks around our data structures like zserv.fair_teams_player_timers and
# zserv.fair_teams_team_timer_running.
###

def fair_teams(event, zserv):
    ###
    # We put this here so it's not picked up by inspect() looking for
    # functions.
    ###
    from ZDStack import get_zdslog
    zdslog = get_zdslog()
    if not hasattr(zserv, 'fair_teams_balance_window'):
        zserv.fair_teams_balance_window = BALANCE_WINDOW
    if not hasattr(zserv, 'fair_teams_player_timers'):
        zserv.fair_teams_player_timers = list()
    if not hasattr(zserv, 'fair_teams_team_timer_running'):
        zserv.fair_teams_team_timer_running = False
    if not zserv.game_mode in TEAM_MODES:
        return
    if not event.type in ('team_switch', 'team_join', 'disconnection'):
        return
    zdslog.debug("Player Timers: %s" % (zserv.fair_teams_player_timers))
    _ds = "Team Timer Running: %s"
    zdslog.debug(_ds % (zserv.fair_teams_team_timer_running))
    zdslog.debug("Event Type: %s" % (event.type))
    try:
        player = zserv.players.get(event.data['player'])
    except PlayerNotFoundError:
        ###
        # Meh.
        ###
        return
    spec_colors = [x for x in TEAM_COLORS if x not in zserv.playing_colors]
    max_teams = len(zserv.playing_colors)
    playing_players = len([x for x in zserv.players if x.playing])
    min_players = playing_players / max_teams
    max_players = min_players + (playing_players % max_teams)

    def _get_losing_teams():
        """Returns a list of the teams that have the lowest scores."""
        losing_team_colors = []
        for playing_color in zserv.playing_colors:
            if not losing_team_colors:
                losing_team_colors.append(playing_color)
            else:
                score = zserv.team_scores[playing_color]
                losing_score = zserv.team_scores[losing_team_colors[0]]
                if score < losing_score:
                    losing_team_colors = [playing_color]
                elif score == losing_score:
                    losing_team_colors.append(playing_color)
        return losing_team_colors

    def _get_team_members(team_color):
        with zserv.players.lock:
            x = zserv.players
            return [y for y in x if y.color == team_color and y.playing]

    def _count_team_members(team_color):
        return len(_get_team_members(team_color))

    def _group_teams():
        above_average = []
        within_range = []
        below_average = []
        for playing_color in zserv.playing_colors:
            num_players = _count_team_members(playing_color)
            if num_players > max_players:
                above_average.append(playing_color)
            elif num_players < min_players:
                below_average.append(playing_color)
            else:
                within_range.append(playing_color)
        return (above_average, within_range, below_average)

    def _check_teams(above_average):
        ###
        # If players disconnect, it the obligation of the other team's players
        # to switch over and even the teams up again.  We want to give them a
        # little time to do so, so we set a timer and inform the players.
        ###
        if not above_average:
            return
        elif len(above_average) == 3:
            msg1 = "The %s, %s and %s teams have too many players, even the "
            msg2 = "teams within %d seconds or random players from offending "
            msg3 = "teams will be kicked"
        elif len(above_average) == 2:
            msg1 = "The %s and %s teams have too many players, even the "
            msg2 = "teams within %d seconds or random players from offending "
            msg3 = "teams will be kicked"
        elif len(above_average) == 1:
            msg1 = "The %s team has too many players, even the teams within "
            msg2 = "%d seconds or random players from offending teams will "
            msg3 = "be kicked"
        msg = msg1 + msg2 + msg3
        t = Timer(zserv.fair_teams_balance_window, _team_retribution,
                  args=[True])
        t.start()
        zserv.fair_teams_team_timer_running = True
        msg = msg % tuple(above_average + [zserv.fair_teams_balance_window])
        zserv.zsay(msg)

    def _player_retribution(player, new_team, check_again, timer):
        zdslog.debug("This is _player_retribution")
        zserv.fair_teams_player_timers.remove(timer)
        zdslog.debug("Player.color: %s" % (player.color))
        zdslog.debug("New_team: %s" % (new_team))
        if player.playing and player.color == new_team:
            zdslog.debug("Player has not switched teams")
            max_teams = len(zserv.playing_colors)
            playing_players = len([x for x in zserv.players if x.playing])
            min_players = playing_players / max_teams
            max_players = min_players + (playing_players % max_teams)
            above_average, within_range, below_average = _group_teams()
            losing_teams = _get_losing_teams()
            if new_team in above_average:
                zserv.zkick(player.number, "Please don't unbalance the teams")
            elif new_team not in losing_teams and new_team not in below_average:
                msg = "Please don't join the winning team unless it needs "
                msg += "players"
                zserv.zkick(player.number, msg)
            else:
                zdslog.debug("Player avoided a swift kick")
        if not zserv.fair_teams_team_timer_running and check_again:
            ###
            # We're not checking for a specific player this time, so do a
            # _check_teams()
            ###
            _check_teams(False)

    def _team_retribution(check_again):
        zserv.fair_teams_team_timer_running = False
        max_teams = len(zserv.playing_colors)
        playing_players = len([x for x in zserv.players if x.playing])
        min_players = playing_players / max_teams
        max_players = min_players + (playing_players % max_teams)
        above_average, within_range, below_average = _group_teams()
        for team in above_average:
            members = _get_team_members(team)
            for x in range(len(members) - max_players):
                player_number = random.choice(members).number
                zserv.kick(player_number, "Keep the teams balanced")
                members = _get_team_members(team)
        if check_again:
            _check_teams(False)

    losing_teams = _get_losing_teams()
    zdslog.debug("Losing Teams: %s" % (losing_teams))
    above_average, within_range, below_average = _group_teams()
    zdslog.debug("Above Average: %s" % (above_average))
    zdslog.debug("Below Average: %s" % (below_average))

    if event.type in ('team_join', 'team_switch'):
        team = event.data['team'].lower()
        zdslog.debug("Team: %s" % (team))
        try:
            player = zserv.players.get(name=event.data['player'])
        except PlayerNotFoundError:
            ###
            # Meh.
            ###
            return
        if not player.playing:
            ###
            # We don't care what spectators do.
            ###
            return
        zdslog.debug("Player: %s" % (player))
        ###
        # There's a couple offenses a player can commit:
        #   - Joining/Switching to a team in above_average
        #   - Joining/Switching to a team that isn't losing and isn't in
        #     below_average
        ###
        if team in above_average:
            msg3 = "unbalancing teams."
        elif team not in losing_teams and team not in below_average:
            msg3 = "joining the winning team."
        else:
            return
        for player_timer in zserv.fair_teams_player_timers:
            if player == player_timer.args[0]:
                ###
                # Clock's already ticking, leave this one alone for now.
                ###
                return
        ###
        # At this point, this player does not yet have a timer waiting on
        # them.
        #
        # Players may just be trading teams to balance in terms of skill,
        # so we don't want to just knee-jerk kick these players.  Instead,
        # give this team "BALANCE_WINDOW" seconds to send another player
        # over.
        ###
        msg1 = "The %s team has too many players, even the teams within %d "
        msg2 = "seconds, or %s will be kicked for "
        m = msg1 + msg2 + msg3
        m = m % (team, zserv.fair_teams_balance_window, player.name)
        zserv.zsay(m)
        args = [player, team, True]
        t = Timer(zserv.fair_teams_balance_window, _player_retribution,
                  args=args)
        args.append(t)
        zserv.fair_teams_player_timers.append(t)
        t.start()
    elif not zserv.fair_teams_team_timer_running:
        ###
        # Player(s) have disconnected, so players from the other team might
        # need to switch over to fill the gaps.
        ###
        _check_teams(above_average)

