import re
from ZDStack.LogEvent import LogEvent

NUMS_TO_WEAPONS = {'1': 'fist', '2': 'chainsaw', '3': 'pistol',
                   '4': 'shotgun', '5': 'super shotgun', '6': 'chaingun',
                   '7': 'rocket launcher', '8': 'plasma rifle', '9': 'bfg',
                   '10': 'telefrag', '11': 'unknown', '12': 'suicide',
                   '13': 'telefuck'}

REGEXPS_AND_RCONS = \
    [(r"^RCON for (.*) is denied!$", 'rcon_denied'),
     (r"^RCON for (.*) is granted!$", 'rcon_granted'),
     (r"^(.*) RCON \((.*) \)$", 'rcon_action')]

REGEXPS_AND_COMMANDS = \
    [(r"^Unknown command (?P<command>.*)$", 'unknown_command'),
     (r"(?P<players>\d\d|\d) players$", 'number_of_players'),
     (r'(?P<player_num>\d\d|\d):  (?P<player_name>.*) \((?P<player_ip>(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d)\.(?:\d\d\d|\d\d|\d))',
      'player_line')]

REGEXPS_AND_WEAPONS = []
REGEXPS_AND_DEATHS = []
REGEXPS_AND_CONNECTIONS = []
REGEXPS_AND_JOINS = []
REGEXPS_AND_FLAGS = []

def line_to_death_event(event_dt, line):
    for regexp, weapon in REGEXPS_AND_WEAPONS:
        match = re.match(regexp, line)
        if match:
            d = {'fragger': match.group(2), 'fraggee': match.group(1),
                 'weapon': weapon}
            return LogEvent(event_dt, 'frag', d)
    for regexp, death in REGEXPS_AND_DEATHS:
        match = re.match(regexp, line)
        if match:
            d = {'fragger': match.group(1), 'fraggee': match.group(1),
                 'weapon': death}
            return LogEvent(event_dt, 'death', d)

def line_to_connection_event(event_dt, line):
    for regexp, x in REGEXPS_AND_CONNECTIONS:
        match = re.match(regexp, line)
        if match:
            d = {'player': match.group(1)}
            return LogEvent(event_dt, x, d)

def line_to_join_event(event_dt, line):
    for regexp, join in REGEXPS_AND_JOINS:
        match = re.match(regexp, line)
        if match:
            d = {'player': match.group(1)}
            if join.startswith('team'):
                d['team'] = match.group(2).lower()
            return LogEvent(event_dt, join, d)

def line_to_rcon_event(event_dt, line):
    for regexp, rcon in REGEXPS_AND_RCONS:
        match = re.match(regexp, line)
        if match:
            d = {'player': match.group(1)}
            if rcon == 'rcon_action':
                d['action'] = match.group(2)
            return LogEvent(event_dt, rcon, d)

def line_to_flag_event(event_dt, line):
    for regexp, flag in REGEXPS_AND_FLAGS:
        match = re.match(regexp, line)
        if match:
            return LogEvent(event_dt, flag, {'player': match.group(1)})

def line_to_map_event(event_dt, line):
    match = re.match('^map(\d\d): (.*)$', line)
    if match:
        d = {'name': match.group(2), 'number': int(match.group(1))}
        return LogEvent(event_dt, 'map_change', d)

def line_to_command_event(event_dt, line):
    for regexp, cmd in REGEXPS_AND_COMMANDS:
        match = re.match(regexp, line)
        if match:
            return LogEvent(event_dt, cmd, match.groupdict())

