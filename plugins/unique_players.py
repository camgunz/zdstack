################################################################################
#                                                                              #
# Unique Players ZDStack Plugin                                                #
#                                                                              #
#   This plugin kicks players with non-unique names.                           #
#                                                                              #
#   Because ZDaemon does not log player IP addresses along with their actions, #
#   if more than one player in a server has the same name, ZDStack can't       #
#   discern which of them the action belongs to.  This plugin immediately      #
#   removes players with non-unique names, ensuring that statistics are        #
#   assigned correctly.  It is highly recommended that this plugin be enabled  #
#   whenever events are enabled (of course, plugins must be enabled as well).  #
#                                                                              #
################################################################################

from __future__ import with_statement

def unique_players(event, zserv):
    ###
    # Really, this should monkeypatch PlayersList.add() for every zserv.
    ###
    if not event.type == 'player_lookup':
        return
    reason = "Player names must unique, %s is already in use"
    player_name = event.data['player_name']
    found = False
    with zserv.players.lock:
        for p in zserv.players:
            if p.name == player_name:
                found = found or p.ip
                if p.ip != found:
                    ###
                    # We don't want to kick players who rejoin while their old
                    # connection is timing out... this plugin would kick the
                    # actual player and leave the "ghost" player.  So players
                    # with the same name and also the same IP address are
                    # allowed.  Most of the time this shouldn't happen, because
                    # PlayersList.add() figures out if a player's reconnected
                    # or not already - this is just to be safe.
                    #
                    # It would be nice if we set a timer on the new player
                    # though; if the old player doesn't disconnect in say...
                    # 60 seconds, the new player is kicked.
                    #
                    # At this point, the name is non-unique.
                    ###
                    zserv.zkick(p.number, reason % (p.name))
                    break

