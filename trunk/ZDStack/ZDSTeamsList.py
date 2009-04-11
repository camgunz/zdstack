from __future__ import with_statement

import logging

from threading import Lock
from collections import deque

from ZDStack import TEAM_COLORS, TeamNotFoundError
from ZDStack.ZDSDatabase import get_team_color

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

    def clear(self):
        """Clears the team list."""
        with self.lock:
            self.__teams = dict()

    def add(self, color, acquire_lock=True):
        """Adds a team.

        color:        a string representing the color of the new team.
        acquire_lock: a boolean that, if True, causes this method to
                      acquire the team lock before adding a team.
                      True by default.

        """
        logging.debug("add(%s, acquire_lock=%s)" % (color, acquire_lock))
        def blah():
            if color not in TEAM_COLORS:
                raise ValueError("Unsupported team color %s" % (color))
            tc = get_team_color(color=color)
            if tc not in self.__teams.keys():
                self.__teams[tc] = deque()
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def get(self, color, acquire_lock=True):
        """Returns a team.

        color:        a string representing the color of the team to
                      return.
        acquire_lock: a boolean that, if True, causes this method to
                      acquire the team lock before getting a team.
                      True by default.

        """
        logging.debug("get(%s, acquire_lock=%s)" % (color, acquire_lock))
        def blah():
            self.add(color, acquire_lock=False)
            for tc in self.__teams.keys():
                if tc.color == color:
                    return tc
            ###
            # This should never happen.
            ###
            raise TeamNotFoundError(color)
        if acquire_lock:
            with self.lock:
                return blah()
        else:
            return blah()

    def get_members(self, color, acquire_lock=True):
        """Returns a deque of a team's members.

        color:        the color of the team whose members are to be
                      returned.
        acquire_lock: a boolean that, if True, will acquire the team
                      lock before getting a team's members.  True by
                      default.

        """
        logging.debug("get_members(%s, acquire_lock=%s)" % (color, acquire_lock))
        if acquire_lock:
            with self.lock:
                return self.__teams[self.get(color, acquire_lock=False)]
        else:
            return self.__teams[self.get(color, acquire_lock=False)]

    def get_player_team(self, player, acquire_lock=True):
        """Returns a player's team.

        player:       a Player instance.
        acquire_lock: a boolean that, if true, will acquire the team
                      lock before getting a player's team.  True by
                      default.

        """
        logging.debug("get_player_team(%s, acquire_lock=%s)" % (player, acquire_lock))
        def blah():
            for tc in self.__teams.keys():
                logging.debug("Checking team %s for %s" % (tc.color, player.name))
                if self.contains_player(tc.color, player, acquire_lock=False):
                    logging.debug("Found team %s" % (tc.color))
                    return tc
        if acquire_lock:
            with self.lock:
                return blah()
        else:
            return blah()

    def set_player_team(self, player, color, acquire_lock=True):
        """Sets the player's team.

        player:       a player instance.
        color:        a string representing the color of the team to
                      which player is to be added.
        acquire_lock: an optional boolean that, if True, acquires this
                      TeamsList's lock before setting a player's team.
                      Defaults to True.

        """
        logging.debug("set_player_team(%s, %s)" % (player, color))
        def blah():
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
            with self.zserv.players.lock:
                player.playing = future_team.color in self.zserv.playing_colors
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def contains_player(self, color, player, acquire_lock=True):
        """Returns True if a player is a member of the specified team.

        color:        a string representing the color of the team to be
                      checked for membership.
        player:       a Player instance.
        acquire_lock: a boolean that, if True, will acquire the team
                      lock before checking if a player is a member of
                      a team.  True by default.

        """
        logging.debug("contains_player(%s, %s, acquire_lock=%s)" % (color, player, acquire_lock))
        def blah():
            self.add(color, acquire_lock=False)
            return player in self.get_members(color, acquire_lock=False)
        if acquire_lock:
            with self.lock:
                return blah()
        else:
            return blah()

