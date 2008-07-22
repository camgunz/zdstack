import time
from threading import Timer, Thread

###
# TODO:
#   Add anti-votespam protection
#   Add per-player vote limit (one player, one vote)
###
RESET_STRING = '!callvote reset'
MAP_STRING = '!callvote map'
KICK_STRING = '!callvote kick'
VOTE_STRING = '!vote'
MAP_PERCENT = 51.0
KICK_PERCENT = 75.0
VOTE_DURATION = 30
VOTE_INTERVAL = 5
VOTING = False
YES_VOTES = 0

def callvote(event, zserv):
    global VOTING
    global YES_VOTES
    reminders = (VOTE_DURATION / VOTE_INTERVAL) - 1
    if not event.type == 'message':
        return
    players = len([x for x in zserv.players.values() if not x.disconnected])
    def _announce_vote(votetype, remaining, value=None):
        suffix = ' %d/%d, %d seconds left' % (YES_VOTES, players, remaining)
        if votetype == 'reset':
            zserv.zsay("Voting to reset map:" + suffix)
        elif votetype == 'map':
            if not value:
                raise ValueError("Value must be given for map change")
            s = "Voting to change map to %s:" + suffix
            zserv.zsay(s % (value, YES_VOTES, players)
        elif votetype == 'kick':
            if not value:
                raise ValueError("Value must be given for player kick")
            s = "Voting to kick player %s:" + suffix
            zserv.zsay(s % (value, YES_VOTES, players)
        else:
            raise ValueError("Invalid vote type %s" % (votetype))
    def _remind_vote(votetype, value=None):
        while reminders:
            _announce_vote(votetype, VOTE_INTERVAL * reminders, value=value)
            reminders -= 1
            time.sleep(VOTE_INTERVAL)
    def _check_vote(votetype, method, args=[], kwargs={}):
        if votetype in ('reset', 'map'):
            threshold = MAP_PERCENT
        elif votetype in ('kick'):
            threshold = KICK_PERCENT
        else:
            raise ValueError("Invalid vote type %s" % (votetype))
        if (float(YES_VOTES) / float(players)) * 100.0 > threshold:
            zserv.zsay("Vote passed!")
            method(*args, **kwargs)
        else:
            zserv.zsay("Vote failed!")
        VOTING = False
        YES_VOTES = 0
    def _start_vote(votetype, value=None):
        if VOTING:
            zserv.zsay("A vote is already taking place")
            return
        VOTING = True
        if votetype in ('reset', 'map'):
            method = zserv.change_map
            if votetype == reset:
                args = ['map' + str(zserv.map['number']).zfill(2)]
            else:
                args = [value]
        elif votetype == 'kick':
            method = zserv.zkick
            args = [zserv.get_player_number(value)]
        _announce_vote(votetype, remaining=VOTE_DURATION, value=value)
        Timer(VOTE_DURATION, _check_vote, args=[votetype], kwargs={'args': args}).start()
        Thread(_remind_vote, args=[votetype, value]).start()
    if event.data['contents'].startswith(RESET_STRING):
        _start_vote('reset')
    elif event.data['contents'].startswith(MAP_STRING):
        _start_vote('map', event.data['contents'].split()[-1])
    elif event.data['contents'].startswith(KICK_STRING):
        _start_vote('kick', event.data['contents'].split()[-1])
    elif event.data['contents'].startswith(VOTE_STRING):
        if not VOTING:
            zserv.zsay("No current vote")
            return
        if event.data['contents'].split()[-1].lower().strip() == 'yes':
            YES_VOTES += 1

