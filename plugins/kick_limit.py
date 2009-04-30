################################################################################
#                                                                              #
# Kick Limit ZDStack Plugin                                                    #
#                                                                              #
#   This plugin temporarily bans players that exceed the kick limit.           #
#                                                                              #
#   Rather than have every plugin keep track of players that are kicked, this  #
#   plugin allows administrators to take more permanent action against         #
#   determined players.  The kick limit, as well as the duration of the        #
#   temporary ban is configurable here.                                        #
#                                                                              #
################################################################################

from __future__ import with_statement

KICK_LIMIT = 2
BAN_LENGTH = 15 # 15 minutes

from ZDStack import PlayerNotFoundError

def kick_limit(event, zserv):
    if not event.type == 'kick_command':
        return
    with zserv.players.lock:
        try:
            player_name = event.data['player_name']
            player = zserv.players.get(name=player_name, acquire_lock=False)
        except PlayerNotFoundError:
            return
        if not hasattr(player, 'number_of_kicks'):
            player.number_of_kicks = 0
        player.number_of_kicks += 1
        if player.number_of_kicks >= KICK_LIMIT:
            player.number_of_kicks = 0
            reason = "Exceeded the kick limit - %d minute ban" % (BAN_LENGTH)
            zserv.zaddtimedban(BAN_LENGTH, player.ip, reason=reason)

