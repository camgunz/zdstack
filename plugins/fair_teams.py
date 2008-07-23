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
        d = dict([(x, len([y for y in zserv.players.values() if y.color == x])) \
                      for x in zserv.teams.values()])
        d = {}
        for c in colors:
            tp = [x for x in zserv.players.values() if x.color == c]
            d[t.color] = len(tp)
        average = sum(d.values()) / len(colors)
        above_average = [x for x in d if d[x] > average]
        below_average = [x for x in d if d[x] <= average]
        if event.data['team'] in above_average:
            
