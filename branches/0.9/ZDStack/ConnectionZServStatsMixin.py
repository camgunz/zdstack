import os.path

from base64 import b64encode

from ZDStack import get_logfile_suffix, debug
from ZDStack.LogFile import LogFile
from ZDStack.PlayerDB import save_player_ip
from ZDStack.LogParser import ConnectionLogParser
from ZDStack.LogListener import ConnectionLogListener

class ConnectionZServStatsMixin:

    def __init__(self):
        f1 = (self.start_collecting_connection_stats, [], {})
        f2 = (self.stop_collecting_connection_stats, [], {})
        self.pre_spawn_funcs.append(f1)
        self.post_spawn_funcs.append(f2)
        debug("Added IP Log Mixin")

    def initialize_connection_log(self):
        debug()
        connection_log_parser = ConnectionLogParser()
        self.connection_log = LogFile('connection', connection_log_parser, self)
        self.connection_log_listener = ConnectionLogListener(self)
        self.connection_log.listeners = [self.connection_log_listener]
        self.connection_log_listener.start()
        self.set_connection_log_filename()
        self.connection_log.start()

    def start_collecting_connection_stats(self):
        debug()
        self.initialize_connection_log()

    def stop_collecting_connection_stats(self):
        debug()
        self.connection_log.stop()
        self.connection_log_listener.stop()

    def get_connection_log_filename(self, roll=False):
        debug()
        return os.path.join(self.homedir, 'conn' + get_logfile_suffix(roll))

    def set_connection_log_filename(self, roll=False):
        debug()
        connection_log_filename = self.get_connection_log_filename(roll=roll)
        self.connection_log.set_filepath(connection_log_filename,
                                         seek_to_end=not roll)

    def log_ip(self, player_name, player_ip):
        debug()
        save_player_ip(player_name, b64encode(player_name), player_ip)

