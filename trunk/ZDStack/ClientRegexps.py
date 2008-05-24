import re

from ZDStack.LogEvent import LogEvent
from ZDStack.BaseRegexps import *

REGEXPS_AND_WEAPONS = \
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

REGEXPS_AND_DEATHS = \
    [(r"^(.*) should have stood back.$", 'rocket suicide'),
     (r"^(.*) mutated.$", 'mutation'),
     (r"^(.*) died.$", 'death'),
     (r"^(.*) melted.$", 'melting'),
     (r"^(.*) killed himself.$", 'suicide'),
     (r"^(.*) fell too far.$", 'falling'),
     (r"^(.*) tried to leave.$", "exiting"),
     (r"^(.*) can't swim.$", "drowning"),
     (r"^(.*) checks his glasses.$", 'teamkill')]

REGEXPS_AND_JOINS = \
    [(r"^(.*) is now on the (Blue|Red|White|Green) team.$", 'team_switch'),
     (r"^(.*) joined the game.$", 'game_join'),
     (r"^(.*) joined the game on the (Blue|Red|White|Green) team.$", 'team_join')]

REGEXPS_AND_FLAGS = \
    [(r"^(.*) has taken the (.*) flag", 'flag_touch'),
     (r"^(.*) lost the (.*) flag", 'flag_loss'),
     (r"^(.*) returned the (.*) flag", 'flag_return'),
     (r"^(.*) picked up the (.*) flag", 'flag_pick'),
     (r"^(.*) scored for the (.*) team", 'flag_cap')]

REGEXPS_AND_CONNECTIONS = \
    [(r"^(.*) has connected.$", 'connection'),
     (r"^(.*) disconnected$", 'disconnection')]

