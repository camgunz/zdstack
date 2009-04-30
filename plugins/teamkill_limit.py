################################################################################
#                                                                              #
# Teamkill Limit ZDStack Plugin                                                #
#                                                                              #
#   This plugin kicks players who exceed the limit on teamkilling.             #
#                                                                              #
#   Players who violate these rules are warned, and subsequently temporarily   #
#   banned upon reaching or exceeding the teamkill limit.  The limit, as well  #
#   as the duration of the temporary ban is configurable by setting the values #
#   of the TEAMKILL_LIMIT and BAN_LENGTH variables respectively.               #
#                                                                              #
################################################################################

from __future__ import with_statement

from ZDStack.ZServ import FFA_MODES, DUEL_MODES

TEAMKILL_LIMIT = 5
BAN_LENGTH = 15 # 15 minutes

def ban_teamkillers(event, zserv):
    if not event.type == 'frag' or not 'fragger' in event.data or \
           zserv.game_mode in FFA_MODES + DUEL_MODES:
        ###
        # Ignore non-frag events and suicides.  Also in a FFA or Duel, player
        # colors will both be None, so ignore those modes too.
        ###
        return
    try:
        ###
        # Cover all our bases here and monkeypatch both fragger and fraggee.
        ###
        fragger = zserv.players.get(name=event.data['fragger'])
        if not hasattr(fragger, 'teamkills'):
            fragger.teamkills = 0
        fraggee = zserv.players.get(name=event.data['fraggee'])
        if not hasattr(fraggee, 'teamkills'):
            fraggee.teamkills = 0
    except PlayerNotFoundError:
        return
    if fragger.color == fraggee.color:
        fragger.teamkills += 1
    if fragger.teamkills == (TEAMKILL_LIMIT - 1):
        msg = "%s, one more teamkill and you will be temporarily banned "
        msg += "for %d minutes"
        zserv.zsay(msg % (fragger.name, BAN_LENGTH))
    elif fragger.teamkills >= TEAMKILL_LIMIT:
        fragger.teamkills = 0
        reason = 'Exceeded the teamkill limit - %d minute ban' % (BAN_LENGTH)
        zserv.zaddtimedban(BAN_LENGTH, fragger.ip, reason)

