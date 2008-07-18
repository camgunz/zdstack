import re

class Regexps:

    COMMANDS = \
        [
         (r'^Unknown command "(?P<command>.*)"$', 'unknown_command'),
         (r"^(?P<player_ip>(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)) added to banlist$", 'addban_command'),
         (r"^couldn't find (?P<bot_name>.*) in bots.cfg$", 'addbot_command'),
         (r"^(?P<player_ip>(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)) \((?P<reason>.*)\)$", 'banlist_command'),
         (r"^Cleared (?P<cleared_maps>\d\d\d|\d\d|\d) maps from que.$", 'clearmaplist_command'),
         (r'^"(?P<var_name>.*)" is "(?P<var_value>.*)"$', 'get_command'),
         (r"^\s.\*\*\s*Player (?P<player_num>\d\d|\d) not found!$", 'kick_command'),
         (r"^>\s*(?P<player_name>.*) was kicked from the game (?P<reason>)$", 'kick_command'),
         (r"^(?P<player_ip>(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)\.(?:\d\d\d|\d\d|\d|\*)) unbanned.$", 'killban_command'),
         (r"^No such ban$", 'killban_command'),
         (r"^(?P<sequence_number>\d\d\d|\d\d|\d)\. (?P<map_number>.*)$", 'maplist_command'),
         (r'^(?P<player_num>\d\d|\d):\s*(?P<player_name>.*)\s\((?P<player_ip>(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d))', 'players_command'),
         (r"^Removed all bots.$", 'removebots_command'),
         (r"^> === ALL SCORES RESET BY SERVER ADMIN ===$", 'resetscores_command'),
         (r"^\] CONSOLE \[ (?P<message>.*)$", 'say_command'),
         (r"^> (?P<var_name>.*) is now (?P<var_value>.*)$", 'set_command'),
         (r"^(?P<wad_number>\d\d\d|\d\d|\d)\. (?P<wad_name>.*.wad)$", 'wads_command')
        ]

    NUMS_TO_WEAPONS = {'1': 'fist', '2': 'chainsaw', '3': 'pistol',
                       '4': 'shotgun', '5': 'super shotgun', '6': 'chaingun',
                       '7': 'rocket launcher', '8': 'plasma rifle', '9': 'bfg',
                       '10': 'telefrag', '11': 'unknown', '12': 'suicide',
                       '13': 'telefuck'}

    RCONS = \
        [(r"^RCON for (?P<player>.*) is denied!$", 'rcon_denied'),
         (r"^RCON for (?P<player>.*) is granted!$", 'rcon_granted'),
         (r"^(?P<player>.*) RCON \((?P<action>.*) \)$", 'rcon_action')]

    WEAPONS = \
        [(r"^> (?P<fraggee>.*) chewed on (?P<fragger>.*)'s fist.$", 'fist'),
         (r"^> (?P<fraggee>.*) was mowed over by (?P<fragger>.*)'s chainsaw.$", 'chainsaw'),
         (r"^> (?P<fraggee>.*) was tickled by (?P<fragger>.*)'s pea shooter.$", 'pistol'),
         (r"^> (?P<fraggee>.*) chewed on (?P<fragger>.*)'s boomstick.$", 'shotgun'),
         (r"^> (?P<fraggee>.*) was mowed down by (?P<fragger>.*)'s chaingun.$", 'chaingun'),
         (r"^> (?P<fraggee>.*) was splattered by (?P<fragger>.*)'s super shotgun.$", 'super shotgun'),
         (r"^> (?P<fraggee>.*) rode (?P<fragger>.*)'s rocket.$", 'rocket launcher'),
         (r"^> (?P<fraggee>.*) was melted by (?P<fragger>.*)'s plasma gun.$", 'plasma gun'),
         (r"^> (?P<fraggee>.*) couldn't hide from (?P<fragger>.*)'s BFG.$", 'bfg'),
         (r"^> (?P<fraggee>.*) was splintered by (?P<fragger>.*)'s BFG.$", 'bfg'),
         (r"^> (?P<fraggee>.*) was telefragged by (?P<fragger>.*).$", 'telefrag')]

    DEATHS = \
        [(r"^> (?P<fraggee>.*) should have stood back.$", 'rocket suicide'),
         (r"^> (?P<fraggee>.*) mutated.$", 'mutation'),
         (r"^> (?P<fraggee>.*) died.$", 'death'),
         (r"^> (?P<fraggee>.*) melted.$", 'melting'),
         (r"^> (?P<fraggee>.*) killed himself.$", 'suicide'),
         (r"^> (?P<fraggee>.*) killed herself.$", 'suicide'),
         (r"^> (?P<fraggee>.*) fell too far.$", 'falling'),
         (r"^> (?P<fraggee>.*) tried to leave.$", "exiting"),
         (r"^> (?P<fraggee>.*) can't swim.$", "drowning"),
         (r"^> (?P<fraggee>.*) checks her glasses.$", 'teamkill'),
         (r"^> (?P<fraggee>.*) checks his glasses.$", 'teamkill')]

    JOINS = \
        [(r"^> (?P<player>.*) is now on the (?P<team>Blue|Red|White|Green) team.$", 'team_switch'),
         (r"^> (?P<player>.*) joined the game.$", 'game_join'),
         (r"^> (?P<player>.*) joined the game on the (?P<team>Blue|Red|White|Green) team.$",
          'team_join')]

    FLAGS = \
        [(r"^> (?P<player>.*) has taken the (?P<team>.*) flag", 'flag_touch'),
         (r"^> (?P<player>.*) lost the (?P<team>.*) flag", 'flag_loss'),
         (r"^> (?P<player>.*) returned the (?P<team>.*) flag", 'flag_return'),
         (r"^> (?P<player>.*) picked up the (?P<team>.*) flag", 'flag_pick'),
         (r"^> (?P<player>.*) scored for the (?P<team>.*) team", 'flag_cap')]

    CONNECTIONS = \
        [(r"^> (?P<player>.*) has connected.$", 'connection'),
         (r"^> (?P<player>.*) disconnected$", 'disconnection'),
         ("^(?P<timestamp>(?:2|1)\\d{3}(?:-|\\/)(?:(?:0[1-9])|(?:1[0-2]))(?:-|\\/)(?:(?:0[1-9])|(?:[1-2][0-9])|(?:3[0-1]))(?:T|\\s)(?:(?:[0-1][0-9])|(?:2[0-3])):(?:[0-5][0-9]):(?:[0-5][0-9]))\\s(?P<player>(?:.*))\\s\\((?P<ip_address>(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))(?![\\d]).*?has.*?connected$", 'ip_log')]

    COMMANDS = [(re.compile(x), y) for x, y in COMMANDS]
    RCONS = [(re.compile(x), y) for x, y in RCONS]
    WEAPONS = [(re.compile(x), y) for x, y in WEAPONS]
    DEATHS = [(re.compile(x), y) for x, y in DEATHS]
    JOINS = [(re.compile(x), y) for x, y in JOINS]
    FLAGS = [(re.compile(x), y) for x, y in FLAGS]
    CONNECTIONS = [(re.compile(x), y) for x, y in CONNECTIONS]
    ALL = COMMANDS + RCONS + WEAPONS + DEATHS + JOINS + FLAGS + CONNECTIONS

