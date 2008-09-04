TEAMKILL_LIMIT = 5

def ban_teamkillers(event, zserv):
    if not event.type == 'frag':
        return
    fragger = zserv.get_player(event.data['fragger'])
    fraggee = zserv.get_player(event.data['fraggee'])
    ###
    # Cover all our bases here and monkeypatch both fragger and fraggee
    ###
    if not hasattr(fragger, 'teamkills'):
        fragger.teamkills = 0
    if not hasattr(fraggee, 'teamkills'):
        fraggee.teamkills = 0
    fragger.teamkills += 1
    if fragger.team == fraggee.team and fragger.name != fraggee.name:
        if fragger.teamkills == (TEAMKILL_LIMIT - 1):
            msg = "%s, one more teamkill and you will be banned" 
            zserv.zsay(msg % fragger.name)
        elif fragger.teamkills >= TEAMKILL_LIMIT:
            fragger.teamkills = 0
            zserv.zaddban(fragger.ip, 'Teamkill limit reached')

