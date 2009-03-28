import os.path
import logging

from ZDStack.Utils import get_logfile_suffix
from ZDStack.LogFile import LogFile
from ZDStack.PlayerDB import save_player_ip
from ZDStack.LogParser import ConnectionLogParser
from ZDStack.LogListener import ConnectionLogListener

class ConnectionZServStatsMixin:

    """ConnectionZServStatsMixin adds Connection stats to a ZServ."""

    def __init__(self):
        """Initializes a ConnectionZServStatsMixin"""
        f1 = (self.start_collecting_connection_stats, [], {})
        f2 = (self.stop_collecting_connection_stats, [], {})
        self.pre_spawn_funcs.append(f1)
        self.post_spawn_funcs.append(f2)
        logging.info('Added IP Log Mixin')

    def start_collecting_connection_stats(self):
        """Starts collecting connection stats."""
        logging.debug('')
        connection_log_parser = ConnectionLogParser()
        self.connection_log = LogFile('connection', connection_log_parser, self)
        self.connection_log_listener = ConnectionLogListener(self)
        self.connection_log.listeners = [self.connection_log_listener]
        self.connection_log_listener.start()
        self.set_connection_log_filename()
        self.connection_log.start()

    def stop_collecting_connection_stats(self):
        """Stops collecting connection stats."""
        logging.debug('')
        self.connection_log.stop()
        self.connection_log_listener.stop()

    def get_connection_log_filename(self, roll=False):
        """Generates the connection log filename."""
        logging.debug('')
        return os.path.join(self.homedir, 'conn' + get_logfile_suffix(roll))

    def set_connection_log_filename(self, roll=False):
        """Sets the connection log filename.

        roll:  a boolean that, if given, does the following:
                - If the time is 11pm, generates a logfile name for
                  the upcoming day.
                - Does not seek to the end of a file before parsing it
                  for events (if it exists).
               Otherwise, the name generated is for the current day,
               and the ZServ's LogFile will seek to the end of its
               file (if it exists).
        """
        logging.debug('')
        connection_log_filename = self.get_connection_log_filename(roll=roll)
        self.connection_log.set_filepath(connection_log_filename,
                                         seek_to_end=not roll)

    def log_ip(self, player_name, player_ip):
        """Logs an IP in the Player => IP database.

        player_name: a string representing the player's name.
        player_ip:   a string representing the player's IP address.

        """
        logging.debug('')
        ###
        # Player -> IP mapping is disabled until PyXSE is replaced with
        # SQLite
        ###
        # save_player_ip(player_name, player_ip)
        pass

