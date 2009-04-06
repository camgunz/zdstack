import re
import logging
from ZDStack.LogEvent import LogEvent

class LineParser:

    """LineParser parses lines into events."""

    def __init__(self, regexps):
        """Initializes a LinePraser.

        regexps: a class whose member regexps map to event types

        """
        self.regexps = regexps
        regexps_list = [regexps.COMMANDS, regexps.RCONS, regexps.WEAPONS,
                        regexps.DEATHS, regexps.JOINS, regexps.FLAGS,
                        regexps.CONNECTIONS]
        categories_list = ('command', 'rcon', 'weapon', 'death', 'join',
                           'flag', 'connection')
        self.regexps_to_categories = dict(zip(categories_list, regexps_list))

    def generic_line_to_event(self, event_dt, line):
        """Generically parses a line into an event.

        event_dt: a datetime representing the time of the event.
        line:     a string representing the line itself.

        """
        ###
        # I know that this overlaps some of the other methods, but meh.
        ###
        for category, regexps in self.regexps_to_categories.items():
            for regexp, event_type in regexps:
                try:
                    match = re.match(regexp, line)
                except:
                    s = 'Choked on line [%s]' % (line)
                    logging.error(s)
                    raise
                if match:
                    d = match.groupdict()
                    e = LogEvent(event_dt, event_type, d, category, line)
                    logging.debug("Generic line to event returning %s" % (e))
                    logging.debug("Event Data: %s" % (d))
                    return e

    def line_to_death_event(self, event_dt, line):
        """Parses a line into a death event.

        event_dt: a datetime representing the time of the event.
        line:     a string representing the line itself.

        """
        for regexp, weapon in self.regexps.WEAPONS:
            match = re.match(regexp, line)
            if match:
                d = match.groupdict()
                d['weapon'] = weapon
                e = LogEvent(event_dt, 'frag', d, 'weapon', line)
                if not 'fragger' in d:
                    logging.debug("Returning a frag w/o a fragger")
                    logging.debug("Line is %s" % (line))
                return e
        for regexp, death in self.regexps.DEATHS:
            match = re.match(regexp, line)
            if match:
                d = match.groupdict()
                d.update({'fragger': d['fraggee'], 'weapon': death})
                e = LogEvent(event_dt, 'death', d, 'death', line)
                if not 'fragger' in d:
                    logging.debug("Returning a death w/o a fragger")
                    logging.debug("Line is %s" % (line))
                return e

    def line_to_join_event(self, event_dt, line):
        """Parses a line into a join event.

        event_dt: a datetime representing the time of the event.
        line:     a string representing the line itself.

        """
        for regexp, join in self.regexps.JOINS:
            match = re.match(regexp, line)
            if match:
                d = match.groupdict()
                if 'team' in d:
                    d['team'] = d['team'].lower()
                return LogEvent(event_dt, join, d, 'join', line)

    def line_to_map_event(self, event_dt, line):
        """Parses a line into a map event.

        event_dt: a datetime representing the time of the event.
        line:     a string representing the line itself.

        """
        match = re.match('^map(\d\d): (.*)$', line)
        if match:
            d = {'name': match.group(2), 'number': int(match.group(1))}
            return LogEvent(event_dt, 'map_change', d, 'map', line)

    def get_event(self, event_dt, line):
        """Returns a list of events that a line represents.

        event_dt: a datetime representing the time of the event
        line:     a string representing the line itself.

        """
        for f in [self.line_to_death_event,
                  self.line_to_join_event,
                  self.line_to_map_event,
                  self.generic_line_to_event]:
            e = f(event_dt, line)
            if e:
                return [e]
        return []

