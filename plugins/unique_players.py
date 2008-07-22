def unique_players(event, zserv):
    if not event.type == 'ip_log':
        return
    n =  event.data['player']
    a = event.data['ip_address']
    for x, y in zserv.players.iteritems():
        if x == n and not y.disconnected:
            r = "Player names must unique, %s is already in use"
            zserv.zkick(a, r % (n))
            break

