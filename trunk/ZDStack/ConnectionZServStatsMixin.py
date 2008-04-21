import os.path

from base64 import b64encode

from ZDStack import log, get_logfile_suffix
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
        self.log("Added IP Log Mixin")

    def initialize_connection_log(self):
        log("ConnectionZServStatsMixin: initialize_connection_log")
        connection_log_parser = ConnectionLogParser()
        connection_log = LogFile('connection', connection_log_parser, self)
        connection_log_listener = ConnectionLogListener(self)
        connection_log.set_filepath(self.get_connection_log_filename())
        connection_log.listeners = [connection_log_listener]
        connection_log_listener.start()
        connection_log.start()
        self.connection_log = connection_log
        self.connection_log_listener = connection_log_listener

    def start_collecting_connection_stats(self):
        log("ConnectionZServStatsMixin: start_collecting_connection_stats")
        self.initialize_connection_log()

    def stop_collecting_connection_stats(self):
        log("ConnectionZServStatsMixin: stop_collecting_connection_stats")
        self.connection_log.stop()
        self.connection_log_listener.stop()

    def get_connection_log_filename(self, roll=False):
        log("ConnectionZServStatsMixin: get_connection_log_filename")
        return os.path.join(self.homedir, 'conn' + get_logfile_suffix(roll))

    def roll_connection_log(self, log_file_name):
        log("ConnectionZServStatsMixin: roll_connection_log")
        connection_log_filename = self.get_connection_log_filename(roll=True)
        self.general_log.set_filepath(connection_log_filename)

    def log_ip(self, player_name, player_ip):
        log("ConnectionZServStatsMixin: log_ip")
        save_player_ip(player_name, b64encode(player_name), player_ip)

