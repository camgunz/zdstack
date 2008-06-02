import re
import logging
from ZDStack.LogEvent import LogEvent

class LineParser:

    def __init__(self, regexps):
        self.regexps = regexps

    def line_to_command_event(self, event_dt, line):
        for regexp, command in self.regexps.COMMANDS:
            try:
                match = re.match(regexp, line)
            except:
                s = 'Choked on command [%s]' % (command)
                logging.getLogger('').debug(s)
                raise
            if match:
                return LogEvent(event_dt, command, match.groupdict())

    def line_to_death_event(self, event_dt, line):
        for regexp, weapon in self.regexps.WEAPONS:
            match = re.match(regexp, line)
            if match:
                d = {'fragger': match.group(2), 'fraggee': match.group(1),
                     'weapon': weapon}
                return LogEvent(event_dt, 'frag', d)
        for regexp, death in self.regexps.DEATHS:
            match = re.match(regexp, line)
            if match:
                d = {'fragger': match.group(1), 'fraggee': match.group(1),
                     'weapon': death}
                return LogEvent(event_dt, 'death', d)

    def line_to_connection_event(self, event_dt, line):
        for regexp, x in self.regexps.CONNECTIONS:
            match = re.match(regexp, line)
            if match:
                d = {'player': match.group(1)}
                return LogEvent(event_dt, x, d)

    def line_to_join_event(self, event_dt, line):
        for regexp, join in self.regexps.JOINS:
            match = re.match(regexp, line)
            if match:
                d = {'player': match.group(1)}
                if join.startswith('team'):
                    d['team'] = match.group(2).lower()
                return LogEvent(event_dt, join, d)

    def line_to_rcon_event(self, event_dt, line):
        for regexp, rcon in self.regexps.RCONS:
            match = re.match(regexp, line)
            if match:
                d = {'player': match.group(1)}
                if rcon == 'rcon_action':
                    d['action'] = match.group(2)
                return LogEvent(event_dt, rcon, d)

    def line_to_flag_event(self, event_dt, line):
        for regexp, flag in self.regexps.FLAGS:
            match = re.match(regexp, line)
            if match:
                return LogEvent(event_dt, flag, {'player': match.group(1)})

    def line_to_map_event(self, event_dt, line):
        match = re.match('^map(\d\d): (.*)$', line)
        if match:
            d = {'name': match.group(2), 'number': int(match.group(1))}
            return LogEvent(event_dt, 'map_change', d)

    def get_event(self, event_dt, line):
        command_event = self.line_to_command_event(event_dt, line)
        death_event = self.line_to_death_event(event_dt, line)
        connection_event = self.line_to_connection_event(event_dt, line)
        join_event = self.line_to_join_event(event_dt, line)
        rcon_event = self.line_to_rcon_event(event_dt, line)
        flag_event = self.line_to_flag_event(event_dt, line)
        map_event = self.line_to_map_event(event_dt, line)
        return [x for x in [command_event, death_event, connection_event,
                            join_event, rcon_event, flag_event, map_event] if x]


