import re

from ZDStack import get_zdslog
from ZDStack.LogEvent import LogEvent

###
# There are certain strings that make it impossible to determine what is a
# player name and what is a message, for instance:
#
#   '<<!> Ladna> > I think that EFL > yr mom >:('
#
# Here, the player name should be '<!> Ladna> ', but because names have very
# few limits and messages have almost none, there is no algorithm that will
# always return the correct player name.
#
# So instead what we do is create a list of possible player names that will
# be passed to the server.  The first one that matches (this test is done
# within the server itself) is used.
#
# This can be foiled if multiple players join a server with names designed to
# exploit this system, but the solution is simple:
#
#   - Disallow players with non-unique names
#   - Disallow players whose name ends in '> '
#
# Both of these can easily be done with a plugin.
#
###

zdslog = get_zdslog()

###
# Also line-length restrictions aren't observed in this file.  Boo regexps.
###

SERVER_PREFIX = r"^>\s"
OLD_TIMESTAMP_PREFIX = r"^(?:2|1)\d{3}(?:-|\/)(?:(?:0[1-9])|(?:1[0-2]))(?:-|\/)(?:(?:0[1-9])|(?:[1-2][0-9])|(?:3[0-1]))(?:T|\s)(?:(?:[0-1][0-9])|(?:2[0-3])):(?:[0-5][0-9]):(?:[0-5][0-9])"
OLD_SERVER_TIMESTAMP_PREFIX = r"(" + OLD_TIMESTAMP_PREFIX + r" >\s|" + SERVER_PREFIX + r")"
TIMESTAMP_PREFIX = r"^(?:2|1)\d{3}(?:-|\/)(?:(?:0[1-9])|(?:1[0-2]))(?:-|\/)(?:(?:0[1-9])|(?:[1-2][0-9])|(?:3[0-1]))(?:T|\s)(?:(?:[0-1][0-9])|(?:2[0-3])):(?:[0-5][0-9]):(?:[0-5][0-9])\s"
SERVER_TIMESTAMP_PREFIX = r"(" + TIMESTAMP_PREFIX + r">\s|" + SERVER_PREFIX + r")"

__SR = re.compile(r'(<.*?>\s)')
__SB = re.compile(r'(<.*>\s)')
__SD = '> '
__ST = re.compile(TIMESTAMP_PREFIX)

def get_possible_player_names(s):
    ###
    # First lop off the timestamp if it matches
    ###
    ppn = list()
    m = __ST.match(s)
    if m:
        ws = s[m.end():]
    else:
        ws = s
    sm = __SR.match(ws)
    bm = __SB.match(ws)
    if not sm and not bm:
        return ppn
    sm = sm.group(1)
    bm = bm.group(1)
    diff = bm.replace(sm, '')
    if not __SD in diff:
        return sm[1:-2]
    for token in diff.split(__SD)[:-1]:
        if not ppn:
            ppn.append(token)
        else:
            ppn.append(sm + __SD.join([ppn[-1], token]))
    return [sm[1:] + x for x in [''] + ppn]

class Regexp(object):

    def __init__(self, regexp, category, event_type, prefix=None):
        """Initializes a Regexp object.
        
        regexp:     a raw string representing the regexp itself.
        category:   a string representing the category of event this
                    regexp matches.
        event_type: a string representing the type of event this regexp
                    matches.
        prefix:     an optional raw string to be prepended to the
                    regexp.
        
        """
        self.category = category
        self.event_type = event_type
        try:
            if prefix:
                s = prefix + regexp
            else:
                s = regexp
            self.regexp = re.compile(s)
        except Exception, e:
            raise Exception("Choked on regexp [%s]: %s" % (s, e))

    def match(self, s):
        """Returns a dict of parsed info from a string.

        s:   a string to parse.

        """
        m = self.regexp.search(s)
        if m:
            return m.groupdict()
        return False

    def get_event(self, s, now=None):
        """Returns an event.

        s:   a string to parse into an event.
        now: a datetime instance representing the time the string was
             generated.

        """
        if s == 'General logging off':
            d = {'log': 'general'}
            zdslog.debug("Returning a log_roll event")
            return LogEvent(now, 'log_roll', d, 'log_roll', s)
        d = self.match(s) # this actually does a 'search', but meh
        if d:
            # zdslog.debug("Returning a %s event" % (self.event_type))
            return LogEvent(now, self.event_type, d, self.category, s)
        ppn = get_possible_player_names(s)
        if ppn:
            d = {'contents': s, 'possible_player_names': ppn}
            return LogEvent(now, 'message', d, 'message', s)
        ###
        # if (s.startswith('<') or (len(s) >= 20 and s[20] == '<')) and '>' in s:
        #     ###
        #     # At this point, the string is probably a message.
        #     ###
        #     tokens = s.split('>')
        #     possible_player_names =  [tokens[0][1:]]
        #     for x in range(1, len(tokens)):
        #         possible_player_names.append('>'.join(tokens[:x])[1:])
        #     zdslog.debug("Returning a message event")
        #     return LogEvent(now, 'message', d, 'message', s)
        ###

class ServerRegexp(Regexp):

    def __init__(self, regexp, category, event_type, requires_prefix=True):
        """Initializes a ServerRegexp.

        requires_prefix: an optional argument.
                         If True, prepends SERVER_TIMESTAMP_PREFIX.
                         If False, prepends TIMESTAMP_PREFIX.
                         If None, prepends r"^".

        All other arguments are the same as Regexp.

        """
        if requires_prefix is True:
            prefix = SERVER_TIMESTAMP_PREFIX
        elif requires_prefix is False:
            prefix = r"^" + TIMESTAMP_PREFIX
        else:
            prefix = r"^"
        Regexp.__init__(self, regexp, category, event_type, prefix)

class ClientRegexp(Regexp):

    def __init__(self, regexp, category, event_type, server_junk=True):
        """Initializes a ClientRegexp.

        Works the same as ServerRegexp, except the prefix is always
        r"^".

        """
        Regexp.__init__(self, regexp, category, event_type, r"^")

COMMANDS = (
(r'Unknown command "(?P<command>.*)"$', 'unknown_command', False),
(r"(?P<player_ip>(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)) added to banlist$", 'addban_command', False),
(r"couldn't find (?P<bot_name>.*) in bots.cfg$", 'addbot_command', False),
(r"(?P<player_ip>(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)) \((?P<reason>.*)\)$", 'banlist_command', False),
(r"Cleared (?P<cleared_maps>\d\d\d|\d\d|\d) maps from que.$", 'clearmaplist_command', False),
(r'"(?P<var_name>.*)" is "(?P<var_value>.*)"$', 'get_command', False),
(r"\s.\*\*\s*Player (?P<player_num>\d\d|\d) not found!$", 'kick_command', False),
(r"(?P<player_name>.*) was kicked from the game (?P<reason>)$", 'kick_command', True),
(r"(?P<player_ip>(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)) unbanned.$", 'killban_command', False),
(r"No such ban$", 'killban_command', False),
(r"map(?P<number>\d\d): (?P<name>.*)$", 'map_change', None),
(r"(?P<sequence_number>\d\d\d|\d\d|\d)\. (?P<map_number>.*)$", 'maplist_command', False),
(r'(?P<player_num>\d\d|\d):\s*(?P<player_name>.*)\s\((?P<player_ip>(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d)):(?P<player_port>\d\d\d\d\d|\d\d\d\d|\d\d\d|\d\d|\d)', 'players_command', False),
(r"Removed all bots.$", 'removebots_command', False),
(r"=== ALL SCORES RESET BY SERVER ADMIN ===$", 'resetscores_command', True),
(r"\] CONSOLE \[ (?P<message>.*)$", 'say_command', False),
(r"(?P<var_name>.*) is now (?P<var_value>.*)$", 'set_command', True),
(r"(?P<wad_number>\d\d\d|\d\d|\d)\. (?P<wad_name>.*.wad)$", 'wads_command', False)
)

RCONS = (
(r"RCON for (?P<player>.*) is denied!$", 'rcon_denied', False),
(r"RCON for (?P<player>.*) is granted!$", 'rcon_granted', False),
(r"(?P<player>.*) RCON \((?P<action>.*) \)$", 'rcon_action', False)
)

FRAGS = (
(r"(?P<fraggee>.*) chewed on (?P<fragger>.*)'s fist.$", 'fist', True),
(r"(?P<fraggee>.*) was mowed over by (?P<fragger>.*)'s chainsaw.$", 'chainsaw', True),
(r"(?P<fraggee>.*) was tickled by (?P<fragger>.*)'s pea shooter.$", 'pistol', True),
(r"(?P<fraggee>.*) chewed on (?P<fragger>.*)'s boomstick.$", 'shotgun', True),
(r"(?P<fraggee>.*) was mowed down by (?P<fragger>.*)'s chaingun.$", 'chaingun', True),
(r"(?P<fraggee>.*) was splattered by (?P<fragger>.*)'s super shotgun.$", 'super shotgun', True),
(r"(?P<fraggee>.*) rode (?P<fragger>.*)'s rocket.$", 'rocket launcher', True),
(r"(?P<fraggee>.*) was melted by (?P<fragger>.*)'s plasma gun.$", 'plasma gun', True),
(r"(?P<fraggee>.*) couldn't hide from (?P<fragger>.*)'s BFG.$", 'bfg', True),
(r"(?P<fraggee>.*) was splintered by (?P<fragger>.*)'s BFG.$", 'bfg', True),
(r"(?P<fraggee>.*) was telefragged by (?P<fragger>.*).$", 'telefrag', True)
)

DEATHS = (
(r"(?P<fraggee>.*) should have stood back.$", 'rocket suicide', True),
(r"(?P<fraggee>.*) mutated.$", 'mutation', True),
(r"(?P<fraggee>.*) died.$", 'death', True),
(r"(?P<fraggee>.*) melted.$", 'melting', True),
(r"(?P<fraggee>.*) killed himself.$", 'suicide', True),
(r"(?P<fraggee>.*) killed herself.$", 'suicide', True),
(r"(?P<fraggee>.*) fell too far.$", 'falling', True),
(r"(?P<fraggee>.*) tried to leave.$", "exiting", True),
(r"(?P<fraggee>.*) can't swim.$", "drowning", True),
(r"(?P<fraggee>.*) checks her glasses.$", 'teamkill', True),
(r"(?P<fraggee>.*) checks his glasses.$", 'teamkill', True)
)

JOINS = (
(r"(?P<player>.*) is now on the (?P<team>Blue|Red|White|Green) team.$", 'team_switch', True),
(r"(?P<player>.*) joined the game.$", 'game_join', True),
(r"(?P<player>.*) joined the game on the (?P<team>Blue|Red|White|Green) team.$", 'team_join', True)
)

FLAGS = (
(r"(?P<team>.*) flag returned", 'auto_flag_return', True),
(r"(?P<player>.*) returned the (?P<team>.*) flag", 'flag_return', True),
(r"(?P<player>.*) has taken the (?P<team>.*) flag", 'flag_touch', True),
(r"(?P<player>.*) lost the (?P<team>.*) flag", 'flag_loss', True),
(r"(?P<player>.*) picked up the (?P<team>.*) flag", 'flag_pick', True),
(r"(?P<player>.*) picked up the (?P<team>.*) flag", 'flag_pick', True),
(r"(?P<player>.*) scored for the (?P<team>.*) team", 'flag_cap', True)
)

CONNECTIONS = (
(r"(?P<ip_address>(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))(?![\d]).*?(?P<port>\d+) connection", 'connection', False),
(r"(?P<player>.*) disconnected$", 'disconnection', True),
(r"(?P<player_name>.*) has connected.$", "player_lookup", True)
)

__CLIENT_REGEXPS = None
__SERVER_REGEXPS = None

###
# We specifically order the regexps because they're searched from left to
# right... so we want the most frequently occurring events to have their
# regexps closer to the left.
#
# Additionally, because the 'set_command' regexp can match team switches,
# COMMANDS have to be after JOINS.
###

def _get_regexps(regexp_maker):
    out = []
    for regexp, event_type, requires_prefix in FRAGS:
        out.append(regexp_maker(regexp, 'frag', event_type, requires_prefix))
    for regexp, event_type, requires_prefix in JOINS:
        out.append(regexp_maker(regexp, 'join', event_type, requires_prefix))
    for regexp, event_type, requires_prefix in COMMANDS:
        out.append(regexp_maker(regexp, 'command', event_type, requires_prefix))
    for regexp, event_type, requires_prefix in CONNECTIONS:
        out.append(regexp_maker(regexp, 'connection', event_type,
                                requires_prefix))
    for regexp, event_type, requires_prefix in FLAGS:
        out.append(regexp_maker(regexp, 'flag', event_type, requires_prefix))
    for regexp, event_type, requires_prefix in DEATHS:
        out.append(regexp_maker(regexp, 'death', event_type, requires_prefix))
    for regexp, event_type, requires_prefix in RCONS:
        out.append(regexp_maker(regexp, 'rcon', event_type, requires_prefix))
    return out

def get_client_regexps():
    global __CLIENT_REGEXPS
    def get_regexp(regexp, category, event_type, requires_prefix):
        return Regexp(regexp, category, event_type, prefix=r"^")
    __CLIENT_REGEXPS = __CLIENT_REGEXPS or _get_regexps(get_regexp)
    return __CLIENT_REGEXPS

def get_server_regexps():
    global __SERVER_REGEXPS
    __SERVER_REGEXPS = __SERVER_REGEXPS or _get_regexps(ServerRegexp)
    return __SERVER_REGEXPS

