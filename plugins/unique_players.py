def unique_players(event, zserv):
    if not event.type == 'ip_log':
        return
    n =  event.data['player']
    a = event.data['ip_address']
    for name, ip in [(p.name, p.ip) for p in zserv.players if p.name]:
        if n == name and a != ip:
            ###
            # We don't want to kick players who rejoin while their old
            # connection is timing out... this plugin would kick the actual
            # player and leave the "ghost" player.  So players with the same
            # name but also the same IP are allowed
            r = "Player names must unique, %s is already in use"
            zserv.zkick(a, r % (n))
            break

