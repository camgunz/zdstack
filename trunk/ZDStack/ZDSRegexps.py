import re

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

###
# Also line-length restrictions aren't observed in this file.  Boo regexps.
###

SERVER_PREFIX = r"^>\s"
TIMESTAMP_PREFIX = r"^(?:2|1)\d{3}(?:-|\/)(?:(?:0[1-9])|(?:1[0-2]))(?:-|\/)(?:(?:0[1-9])|(?:[1-2][0-9])|(?:3[0-1]))(?:T|\s)(?:(?:[0-1][0-9])|(?:2[0-3])):(?:[0-5][0-9]):(?:[0-5][0-9])"
SERVER_TIMESTAMP_PREFIX = r"(" + TIMESTAMP_PREFIX + r" >\s|" + SERVER_PREFIX + r"("

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
        if prefix:
            self.regexp = re.compile(prefix + regexp)
        else:
            self.regexp = re.compile(regexp)
        self.category = category
        self.event_type = event_type

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
            return LogEvent(now, 'log_roll', d, 'log_roll', s)
        d = self.match(s) # this actually does a 'search', but meh
        if d:
            return LogEvent(now, self.event_type, d, self.category, s)
        if s.startswith('<') and '>' in line:
            ###
            # At this point, the string is probably a message.
            ###
            tokens = line.split('>')
            possible_player_names =  [tokens[0][1:]]
            for x in range(1, len(tokens)):
                possible_player_names.append('>'.join(tokens[:x])[1:])
            d = {'contents': line,
                 'possible_player_names': possible_player_names}
            return LogEvent(now, 'message', d, 'message', s)

class ServerRegexp(Regexp):

    def __init__(self, regexp, category, event_type, requires_prefix=True):
        """Initializes a ServerRegexp.

        requires_prefix: an optional boolean that, if given, sets this
                         regexp's prefix to SERVER_TIMESTAMP_PREFIX.
                         True by default, if False, the prefix is set
                         to r"^" instead.

        All other arguments are the same as Regexp.

        """
        if requires_prefix:
            prefix = SERVER_TIMESTAMP_PREFIX
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
(r"*(?P<player_name>.*) was kicked from the game (?P<reason>)$", 'kick_command', True),
(r"(?P<player_ip>(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)) unbanned.$", 'killban_command', False),
(r"No such ban$", 'killban_command', False),
(r"map(?P<number>\d\d): (?P<name>.*)$", 'map_change', False),
(r"(?P<sequence_number>\d\d\d|\d\d|\d)\. (?P<map_number>.*)$", 'maplist_command', False),
(r'(?P<player_num>\d\d|\d):\s*(?P<player_name>.*)\s\((?P<player_ip>(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d)):(?P<player_port>\d\d\d\d\d|\d\d\d\d|\d\d\d|\d\d|\d)', 'players_command', False),
(r"Removed all bots.$", 'removebots_command', False),
(r"=== ALL SCORES RESET BY SERVER ADMIN ===$", 'resetscores_command', True),
(r"\] CONSOLE \[ (?P<message>.*)$", 'say_command', False),
(r"(?P<var_name>.*) is now (?P<var_value>.*)$", 'set_command', True),
(r"(?P<wad_number>\d\d\d|\d\d|\d)\. (?P<wad_name>.*.wad)$", 'wads_command', False)
)

RCONS = (
(r"RCON for (?P<player>.*) is denied!$", 'rcon_denied', True),
(r"RCON for (?P<player>.*) is granted!$", 'rcon_granted', True),
(r"(?P<player>.*) RCON \((?P<action>.*) \)$", 'rcon_action', True)
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
(r"(?P<player>.*) has taken the (?P<team>.*) flag", 'flag_touch', True),
(r"(?P<player>.*) lost the (?P<team>.*) flag", 'flag_loss', True),
(r"(?P<player>.*) returned the (?P<team>.*) flag", 'flag_return', True),
(r"(?P<player>.*) picked up the (?P<team>.*) flag", 'flag_pick', True),
(r"(?P<player>.*) scored for the (?P<team>.*) team", 'flag_cap', True)
)

CONNECTIONS = (
(r"^(?P<ip_address>(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))(?![\d]).*?(?P<port>\d+) connection", 'connection', False),
(r"(?P<player>.*) disconnected$", 'disconnection', True),
(r"(?P<player_name>.*) has connected.$", "player_lookup", True)
)

ALL = COMMANDS + RCONS + WEAPONS + DEATHS + JOINS + FLAGS + CONNECTIONS
CLIENT_REGEXPS = [ClientRegexp(*x) for x in ALL]
SERVER_REGEXPS = [ServerRegexp(*x) for x in ALL]

__CLIENT_REGEXPS = None
__SERVER_REGEXPS = None

###
# We specifically order the regexps because they're searched from left to
# right... so we want the most frequently occurring events to have their
# regexps closer to the left.
###

def get_client_regexps():
    global __CLIENT_REGEXPS
    if __CLIENT_REGEXPS is None:
        for regexp, event_type, requires_prefix in FRAGS:
            x = Regexp(regexp, event_type, 'frag', r"^")
            __CLIENT_REGEXPS.append(x)
        for regexp, event_type, requires_prefix in COMMANDS:
            x = Regexp(regexp, event_type, 'command', r"^")
            __CLIENT_REGEXPS.append(x)
        for regexp, event_type, requires_prefix in JOINS:
            x = Regexp(regexp, event_type, 'join', r"^")
            __CLIENT_REGEXPS.append(x)
        for regexp, event_type, requires_prefix in CONNECTIONS:
            x = Regexp(regexp, event_type, 'connection', r"^")
            __CLIENT_REGEXPS.append(x)
        for regexp, event_type, requires_prefix in FLAGS:
            x = Regexp(regexp, event_type, 'flag', r"^")
            __CLIENT_REGEXPS.append(x)
        for regexp, event_type, requires_prefix in DEATHS:
            x = Regexp(regexp, event_type, 'death', r"^")
            __CLIENT_REGEXPS.append(x)
        for regexp, event_type, requires_prefix in RCONS:
            x = Regexp(regexp, event_type, 'rcon', r"^")
            __CLIENT_REGEXPS.append(x)
    return __CLIENT_REGEXPS

def get_server_regexps():
    global __SERVER_REGEXPS
    if __SERVER_REGEXPS is None:
        for regexp, event_type, requires_prefix in FRAGS:
            x = ServerRegexp(regexp, event_type, 'frag', requires_prefix)
            __SERVER_REGEXPS.append(x)
        for regexp, event_type, requires_prefix in COMMANDS:
            x = ServerRegexp(regexp, event_type, 'command', requires_prefix)
            __SERVER_REGEXPS.append(x)
        for regexp, event_type, requires_prefix in JOINS:
            x = ServerRegexp(regexp, event_type, 'join', requires_prefix)
            __SERVER_REGEXPS.append(x)
        for regexp, event_type, requires_prefix in CONNECTIONS:
            x = ServerRegexp(regexp, event_type, 'connection', requires_prefix)
            __SERVER_REGEXPS.append(x)
        for regexp, event_type, requires_prefix in FLAGS:
            x = ServerRegexp(regexp, event_type, 'flag', requires_prefix)
            __SERVER_REGEXPS.append(x)
        for regexp, event_type, requires_prefix in DEATHS:
            x = ServerRegexp(regexp, event_type, 'death', requires_prefix)
            __SERVER_REGEXPS.append(x)
        for regexp, event_type, requires_prefix in RCONS:
            x = ServerRegexp(regexp, event_type, 'rcon', requires_prefix)
            __SERVER_REGEXPS.append(x)
    return __SERVER_REGEXPS

