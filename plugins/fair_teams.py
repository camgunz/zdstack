from threading import Timer

MIN_PLAYERS = 0
MAX_PLAYERS = 16

BALANCE_WINDOW = 15

def fair_teams(event, zserv):
    if not event.type in ('team_join', 'team_switch'):
        return
    if not zserv.type in ('teamdm', 'ctf'):
        return
    player = zserv.get_player(event.data['player'])
    if max_teams = 2:
        colors = ('red', 'blue')
        spec_colors = ('green', 'white')
    elif max_teams = 3:
        colors = ('red', 'blue', 'green')
        spec_colors = ('white')
    elif max_teams = 4:
        colors = ('red', 'blue', 'green', 'white')
    def _teams_are_unbalanced():
        d = {}
        ps = zserv.players.values()
        for c in colors:
            tp = [x for x in ps if x.color == c and x.playing]
            ps = [x for x in ps if x not in tp]
            d[t.color] = len(tp)
        average = sum(d.values()) / len(colors)
        if average == MAX_PLAYERS:
            upper_bound = MAX_PLAYERS
        else:
            upper_bound = average + 1
        if average == MIN_PLAYERS:
            lower_bound = MIN_PLAYERS
        else:
            lower_bound = average - 1
        above_average = [x for x in d if d[x] >= upper_bound]
        below_average = [x for x in d if d[x] <= lower_bound]
        if not (above_average and below_average):
            return False
        return (above_average, below_average)
    def _kick_unbalancer(p):
        if _teams_are_unbalanced():
            zserv.kick(p.number, "Keep the teams balanced")
    if event.type == 'team_join':
        losing_teams = []
        for team in [y for x, y in zserv.teams.items() if x in colors]:
            if not losing_teams:
                losing_teams = [team]
                continue
            team_players = len(team.players)
            losing_team_players = len(losing_teams[0].players)
            if team_players < losing_team_players:
                losing_teams = [team]
            elif team_players == losing_team_players:
                if zserv.type == 'teamdm':
                    if team.frags < losing_teams[0].frags:
                        losing_teams = [team]
                    elif team.frags == losing_teams[0].frags:
                        losing_teams.append(team)
                elif zserv.type == 'ctf':
                    if team.flag_caps < losing_teams[0].flag_caps:
                        losing_teams = [team]
                    elif team.flag_caps == losing_teams[0].flag_caps:
                        losing_teams.append(team)
            elif zserv.type == 'teamdm':
                if team.frags > losing_teams[0].frags:
                    continue
                elif team.frags == losing_teams[0].frags:
                    team_players = len(team.players)
                    losing_team_players = len(losing_teams[0].players)
                    if team_players < losing_team_players:
                        losing_teams = [team]
                    elif team_players == losing_team_players:
                        losing_teams.append(team)
        colors = [x.color for x in losing_teams] + other_colors
        if not event.data['team'] in colors:
            reason = "Please join the team with the least amount of players,"
            reason += "or if equal, the team that is losing"
            zserv.kick(player.number, reason)
    elif event.type == 'team_switch':
        x = _teams_are_unbalanced()
        if not x:
            return
        above_average, below_average = x
        if event.data['team'] not in above_average:
            return
        if len(above_average) == 3:
            msg1 = "The %s, %s and %s teams have too many players"
        elif len(above_average) == 2:
            msg1 = "The %s and %s teams have too many players"
        else:
            msg1 = "The %s team has too many players"
        msg2 = ", even the teams or %s will be kicked" % (player.name)
        zserv.zsay(msg1 + msg2 % (above_average))
        Timer(BALANCE_WINDOW, _kick_unbalancer, args=[player]).start()

