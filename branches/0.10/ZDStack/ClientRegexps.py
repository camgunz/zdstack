class Regexps:

    NUMS_TO_WEAPONS = {'1': 'fist', '2': 'chainsaw', '3': 'pistol',
                       '4': 'shotgun', '5': 'super shotgun', '6': 'chaingun',
                       '7': 'rocket launcher', '8': 'plasma rifle', '9': 'bfg',
                       '10': 'telefrag', '11': 'unknown', '12': 'suicide',
                       '13': 'telefuck'}

    RCONS = \
        [(r"^RCON for (.*) is denied!$", 'rcon_denied'),
         (r"^RCON for (.*) is granted!$", 'rcon_granted'),
         (r"^(.*) RCON \((.*) \)$", 'rcon_action')]

    COMMANDS = \
        [(r"^Unknown command (?P<command>.*)$", 'unknown_command'),
         (r"(?P<players>\d\d|\d) players$", 'number_of_players'),
         (r'(?P<player_num>\d\d|\d):  (?P<player_name>.*) \((?P<player_ip>(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d))',
          'player_line')]

    WEAPONS = \
        [(r"^(.*) chewed on (.*)'s fist.$", 'fist'),
         (r"^(.*) was mowed over by (.*)'s chainsaw.$", 'chainsaw'),
         (r"^(.*) was tickled by (.*)'s pea shooter.$", 'pistol'),
         (r"^(.*) chewed on (.*)'s boomstick.$", 'shotgun'),
         (r"^(.*) was mowed down by (.*)'s chaingun.$", 'chaingun'),
         (r"^(.*) was splattered by (.*)'s super shotgun.$", 'super shotgun'),
         (r"^(.*) rode (.*)'s rocket.$", 'rocket launcher'),
         (r"^(.*) was melted by (.*)'s plasma gun.$", 'plasma gun'),
         (r"^(.*) couldn't hide from (.*)'s BFG.$", 'bfg'),
         (r"^(.*) was splintered by (.*)'s BFG.$", 'bfg'),
         (r"^(.*) was telefragged by (.*).$", 'telefrag')]

    DEATHS = \
        [(r"^(.*) should have stood back.$", 'rocket suicide'),
         (r"^(.*) mutated.$", 'mutation'),
         (r"^(.*) died.$", 'death'),
         (r"^(.*) melted.$", 'melting'),
         (r"^(.*) killed herself.$", 'suicide'),
         (r"^(.*) killed himself.$", 'suicide'),
         (r"^(.*) fell too far.$", 'falling'),
         (r"^(.*) tried to leave.$", "exiting"),
         (r"^(.*) can't swim.$", "drowning"),
         (r"^(.*) checks her glasses.$", 'teamkill'),
         (r"^(.*) checks his glasses.$", 'teamkill')]

    JOINS = \
        [(r"^(.*) is now on the (Blue|Red|White|Green) team.$", 'team_switch'),
         (r"^(.*) joined the game.$", 'game_join'),
         (r"^(.*) joined the game on the (Blue|Red|White|Green) team.$", 'team_join')]

    FLAGS = \
        [(r"^(.*) has taken the (.*) flag", 'flag_touch'),
         (r"^(.*) lost the (.*) flag", 'flag_loss'),
         (r"^(.*) returned the (.*) flag", 'flag_return'),
         (r"^(.*) picked up the (.*) flag", 'flag_pick'),
         (r"^(.*) scored for the (.*) team", 'flag_cap')]

    CONNECTIONS = \
        [(r"^(.*) has connected.$", 'connection'),
         (r"^(.*) disconnected$", 'disconnection')]

