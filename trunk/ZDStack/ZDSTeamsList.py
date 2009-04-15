from __future__ import with_statement

from threading import Lock
from collections import deque

from ZDStack import TEAM_COLORS, TeamNotFoundError, get_zdslog
from ZDStack.Utils import requires_instance_lock
from ZDStack.ZDSDatabase import get_team_color

zdslog = get_zdslog()

class TeamsList(object):

    def __init__(self, zserv):
        """Initializes a TeamsList.

        zserv: a zserv instance to hold teams for.

        """
        self.zserv = zserv
        self.__teams = dict()
        self.lock = Lock()

    def __iter__(self):
        return self.__teams.__iter__()

    @requires_instance_lock()
    def clear(self):
        """Clears the team list."""
        self.__teams = dict()

    @requires_instance_lock()
    def add(self, color):
        """Adds a team.

        color:        a string representing the color of the new team.

        """
        zdslog.debug("add(%s)" % (color))
        if color not in TEAM_COLORS:
            raise ValueError("Unsupported team color %s" % (color))
        tc = get_team_color(color=color)
        if tc not in self.__teams.keys():
            self.__teams[tc] = deque()

    @requires_instance_lock()
    def get(self, color):
        """Returns a team.

        color:        a string representing the color of the team to
                      return.

        """
        zdslog.debug("get(%s)" % (color))
        self.add(color, acquire_lock=False)
        for tc in self.__teams.keys():
            if tc.color == color:
                return tc
        ###
        # This should never happen.
        ###
        raise TeamNotFoundError(color)

    @requires_instance_lock()
    def get_members(self, color):
        """Returns a deque of a team's members.

        color:        the color of the team whose members are to be
                      returned.

        """
        zdslog.debug("get_members(%s)" % (color))
        return self.__teams[self.get(color, acquire_lock=False)]

    @requires_instance_lock()
    def get_player_team(self, player):
        """Returns a player's team.

        player:       a Player instance.

        """
        zdslog.debug("get_player_team(%s)" % (player))
        for tc in self.__teams.keys():
            zdslog.debug("Checking team %s for %s" % (tc.color, player.name))
            if self.contains_player(tc.color, player, acquire_lock=False):
                zdslog.debug("Found team %s" % (tc.color))
                return tc

    @requires_instance_lock()
    def set_player_team(self, player, color):
        """Sets the player's team.

        player:       a player instance.
        color:        a string representing the color of the team to
                      which player is to be added.

        """
        zdslog.debug("set_player_team(%s, %s)" % (player, color))
        current_team = self.get_player_team(player, acquire_lock=False)
        future_team = self.get(color, acquire_lock=False)
        if current_team:
            ###
            # It's possible for a player to not be on a team yet.
            ###
            if current_team.color == future_team.color:
                ###
                # We only want to go through this if there is actually a
                # change to be made.
                ###
                return
            self.__teams[current_team].remove(player)
        self.__teams[future_team].append(player)
        is_playing = future_team.color in self.zserv.playing_colors
        self.zserv.players.set_playing(player, is_playing)

    @requires_instance_lock()
    def contains_player(self, color, player):
        """Returns True if a player is a member of the specified team.

        color:        a string representing the color of the team to be
                      checked for membership.
        player:       a Player instance.

        """
        zdslog.debug("contains_player(%s, %s)" % (color, player))
        self.add(color, acquire_lock=False)
        return player in self.get_members(color, acquire_lock=False)

