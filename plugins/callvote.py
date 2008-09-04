import time
import datetimei
from threading import Timer, Thread

###
# TODO:
#   Add anti-votespam protection
###
RESET_STRING = '!callvote reset'
MAP_STRING = '!callvote map'
KICK_STRING = '!callvote kick'
VOTE_STRING = '!vote'
MAP_PERCENT = 51.0
KICK_PERCENT = 75.0
VOTE_DURATION = 30
VOTE_INTERVAL = 5
TIME_BETWEEN_VOTECALLS = 5 # minutes
VOTE_SPAM_THRESHOLD = 3
CV_ZSERVS = {}

def callvote(event, zserv):
    global CV_ZSERVS
    reminders = (VOTE_DURATION / VOTE_INTERVAL) - 1
    if not event.type == 'message':
        return
    messenger = zserv.distill_player(event.data['possible_player_names'])
    if not messenger: # for some odd reason, couldn't distill the player
        return

    def _td_to_seconds(td):
        return (td.days * 86400) + td.seconds

    def _get_votes():
        CV_ZSERVS[zserv.name]['players'] = 0
        CV_ZSERVS[zserv.name]['yes_votes'] = 0
        missing_votes = False
        for player in [x for x in zserv.players.values() if x.playing]:
            CV_ZSERVS[zserv.name]['players'] += 1
            if not hasattr(player, 'vote'):
                player.vote = None
                missing_votes = True
            if player.vote == 'yes':
                CV_ZSERVS[zserv.name]['yes_votes'] += 1
            elif player.vote is None:
                missing_votes = True
        _yes_votes = float(CV_ZSERVS[zserv.name]['yes_votes'])
        _players = float(CV_ZSERVS[zserv.name]['players']
        return (_yes_votes / _players, missing_votes)

    def _announce_vote():
        s = ' %d/%d, %d seconds left' % (CV_ZSERVS[zserv.name]['yes_votes'],
                                         CV_ZSERVS[zserv.name]['players'],
                                         remaining)
        if CV_ZSERVS[zserv.name]['votetype'] == 'reset':
            zserv.zsay("Voting to reset map:" + s)
        elif CV_ZSERVS[zserv.name]['votetype'] == 'map':
            zserv.zsay("Voting to change map to %s:" + suffix % (value))
        elif CV_ZSERVS[zserv.name]['votetype'] == 'kick':
            zserv.zsay("Voting to kick player %s:" + suffix % (value))

    def _remind_vote():
        while reminders:
            _announce_vote()
            reminders -= 1
            time.sleep(VOTE_INTERVAL)

    def _check_vote():
        percentage, missing_votes = _get_votes()
        if missing_votes:
            return # voting isn't complete yet
        if percentage > CV_ZSERVS[zserv.name]['threshold']:
            zserv.zsay("Vote passed!")
            CV_ZSERVS[zserv.name]['method'](*CV_ZSERVS[zserv.name]['args'],
                                            **CV_ZSERVS[zserv.name]['kwargs'])
        else:
            zserv.zsay("Vote failed!")
        del CV_ZSERVS[zserv.name]
        for player in zserv.players.values():
            player.vote = None

    def _start_vote(votetype, value=None):
        CV_ZSERVS[zserv.name] = {'threshold': None, 'method': None, 'args': [],
                                 'kwargs': {}, 'players': 0, 'yes_votes': 0,
                                 'votetype': votetype, 'value': None}
        CV_ZSERVS[zserv.name]['votetype'] = votetype
        if votetype in ('reset', 'map'):
            CV_ZSERVS[zserv.name]['method'] = zserv.change_map
            if votetype == reset:
                value = str(zserv.map['number']).zfill(2)
            CV_ZSERVS[zserv.name]['args'] = [value]
            CV_ZSERVS[zserv.name]['threshold'] = [MAP_PERCENT]
        elif votetype == 'kick':
            CV_ZSERVS[zserv.name]['method'] = zserv.addtimedban
            s = 'The players have voted to kick you'
            CV_ZSERVS[zserv.name]['args'] = [10, zserv.get_player_ip(value), s]
            CV_ZSERVS[zserv.name]['threshold'] = [KICK_PERCENT]
        _announce_vote(votetype, remaining=VOTE_DURATION, value=value)
        Timer(VOTE_DURATION, _check_vote).start() # set vote timeout
        Thread(_remind_vote).start()

    def _is_vote_spam():
        s = "%s, you have already called a vote, please don't vote spam"
        now = datetime.datetime.now()
        if not hasattr(messenger, 'called_vote'):
            messenger.called_vote = now
        seconds_since_last_votecall = now - messenger.called_vote
        if seconds_since_last_votecall * 60 < TIME_BETWEEN_VOTECALLS:
            if not hasattr(messenger, 'votespam_warnings'):
                messenger.votespam_warnings = 0
            messenger.votespam_warnings += 1
            if messenger.votespam_warnings >= VOTE_SPAM_THRESHOLD:
                zserv.addtimedban(10, messenger.ip, 'Vote Spamming')
            else:
                zserv.zsay(s % (messenger.name))
            return True
        else:
            return False
            
    if event.data['contents'].startswith(VOTE_STRING):
        if not zserv.name in VOTING:
            zserv.zsay("No current vote")
            return
        if event.data['contents'].split()[-1].lower().strip() == 'yes':
            messenger.vote = 'yes'
        elif event.data['contents'].split()[-1].lower().strip() == 'no':
            messenger.vote = 'no'
        _check_votes()
    elif zserv.name in VOTING:
        zserv.zsay("A vote is already taking place")
    elif not _is_vote_spam():
        if event.data['contents'].startswith(RESET_STRING):
            _start_vote('reset')
        elif event.data['contents'].startswith(MAP_STRING):
            _start_vote('map', event.data['contents'].split()[-1])
        elif event.data['contents'].startswith(KICK_STRING):
            _start_vote('kick', event.data['contents'].split()[-1])

