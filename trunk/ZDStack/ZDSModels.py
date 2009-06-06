from ZDStack import get_engine, get_metadata, get_zdslog
from ZDStack.ZDSTables import *

zdslog = get_zdslog()

###
# Get the DB engine.
###
zdslog.debug("Initializing Database")
__engine = get_engine()
__metadata = get_metadata()

class Alias(object):

    """Alias represents a player's alias.

    .. attribute:: name
        A string representing the alias' name
    .. attribute:: ip_address
        A string representing the alias' IP address

    There is no way for ZDStack to determine player identity
    completely on its own; an administrator must setup mappings between
    StoredPlayers and Aliases.  However, player names and addresses
    must be stored, so we assume that everything is an Alias and store
    it as such.

    """

    def __init__(self, name=None, ip_address=None):
        self.name = name
        self.ip_address = ip_address

    def __str__(self):
        return '<Alias %s>' % (self.name)

    def __repr__(self):
        s = "Alias('%s', '%s')"
        return s % (self.name, self.ip_address)

class TeamColor(object):

    """TeamColor represents a team's color.

    .. attribute:: color
        A string representing the team's color

    .. attribute:: frags
        A list of this team color's Frags

    .. attribute:: deaths
        A list of this team color's Deaths (Frags)

    .. attribute:: flag_touches
        A list of this team color's FlagTouches

    .. attribute:: flag_returns
        A list of this team color's FlagReturns

    Teams can be much more than just colors, for instance, it's
    possible for an IDL 'team' to play different rounds as different
    using different 'team colors'.  So we simply store the team's color
    and require the administrator to create their own mapping between
    whatever they think a 'team' is, and that team's color in the
    round.

    """

    def __init__(self, color=None):
        self.color = color

    def __str__(self):
        return '<TeamColor %s>' % (self.color)

    def __repr__(self):
        return "TeamColor('%s')" % (self.color)

class Wad(object):

    """Wad represents a WAD file.

    .. attribute:: name
        A string representing the name of the wad.

    """

    def __init__(self, name=None):
        self.name = name

    def __unicode__(self):
        return self.name

    __repr__ = __str__ = __unicode__

    @property
    def short_name(self):
        """The short name of this WAD.

        :rtype: unicode
        :returns: the short name of the WAD.  WADs have history of
                  having their names shortened, i.e. ZDCTF or EpicCTF,
                  this method attempts to figure these short-hand names
                  out for the given WAD.

        """
        if self.name == 'zdctfmp.wad':
            return u'ZDCTF'
        elif self.name == 'zdctfmp2.wad':
            return u'ZDCTF2'
        elif self.name == 'zdctfmp3-.wad':
            return u'ZDCTF3'
        elif self.name == u'32in24-4final.wad':
            return u'THIRTY4'
        elif self.name == u'32in24-7.wad':
            return u'THIRTY7'
        elif self.name == u'zdcctfmpc.wad':
            return u'CRAZY'
        elif self.name == u'odactf1.wad':
            return u'ODACTF'
        elif self.name == u'dwango5.wad':
            return u'DWANGO5'
        elif self.name == u'dwango6.wad':
            return u'DWANGO6'
        elif self.name == u'doom2.wad':
            return u'doom2'
        else:
            s = self.name.upper().replace('.wad', '').replace('-', '')
            return s.replace('_', '').decode('utf8')

    @property
    def prefix(self):
        """The prefix of this WAD.

        :rtype: unicode
        :returns: the short name of the WAD.  WADs have history of
                  prefixes assigned to them, i.e. ZDCTF, this method
                  attempts to figure these prefixes out for the given
                  WAD.

        """
        sn = self.short_name
        if sn in (u'ZDCTF2', u'ZDCTF3'):
            return u'ZDCTF'
        if sn == u'ODACTF':
            return u'ODA'
        if sn == u'DWANGO5':
            return u'D5'
        if sn == u'DWANGO6':
            return u'D5'
        return sn in (u'ZDCTF2', u'ZDCTF3') and u'ZDCTF' or sn

class Map(object):

    """Map represents a map in a WAD.

    .. attribute:: id
        The database ID of this Map

    .. attribute:: wad
        The containing WAD

    .. attribute:: number
        An int representing the number of this Map in the containing
        WAD

    .. attribute:: name
        A string representing the name of this Map

    .. attribute:: rounds
        A list of Rounds played on this Map

    """

    def __init__(self, number=None, name=None, wad=None):
        self.number = number
        self.name = name
        if wad:
            self.wad_name = wad.name

    def __unicode__(self):
        return u"<%s: %s>" % (self.short_name, self.name)

    __str__ = __unicode__

    def __repr__(self):
        return u"Map(%s, '%s')" % (self.number, self.name)

    @property
    def short_name(self):
        """The shortname of a map.

        :rtype: unicode
        :returns: the short-hand name of a map.  Maps have a history of
                  shorthand names, i.e. D5M1, E2M1, ZDCTF04, ODA02,
                  etc.  This method attempts to figure these out for
                  the given map.

        """
        if self.wad:
            if u'DWANGO' in self.wad.short_name:
                return self.wad.prefix + u'M' + unicode(self.number)
            return self.wad.prefix + unicode(self.number).zfill(2)
        return u'MAP%s' % (unicode(self.number).zfill(2))

class Weapon(object):

    """Weapon represents something that kills players.

    .. attribute:: name
        A string representing the name of the Weapon
    .. attribute:: is_suicide
        A boolean, whether or not the Weapon is a suicide
    .. attribute: frags
        A list of this Weapon's Frags

    """

    def __init__(self, name=None, is_suicide=False):
        self.name = name
        self.is_suicide = is_suicide

    def __str__(self):
        return '<Weapon %s>' % (self.name)

    def __repr__(self):
        return "Weapon('%s', is_suicide=%s)" % (self.name, self.is_suicide)

class Port(object):

    """Port represents a Doom source port.

    .. attribute:: name
        A string representing the name of this Port

    .. attribute:: game_modes
        A list of this Port's GameModes

    """

    def __init__(self, name=None):
        self.name = name

    def __str__(self):
        return '<Port %s>' % (self.name)

    def __repr__(self):
        return "Port('%s')" % (self.name)

class GameMode(object):

    """GameMode represents a game's mode, i.e. TeamDM, CTF, etc.

    .. attribute:: name
        A string representing this GameMode's name

    .. attribute:: ports
        This GameMode's Port

    .. attribute:: has_teams
        A boolean, whether or not this GameMode employs teams

    .. attribute:: rounds
        A list of Rounds played using this GameMode

    """

    def __init__(self, name=None, has_teams=False):
        self.name = name
        self.has_teams = has_teams

    def __str__(self):
        return '<GameMode %s>' % (self.name)

    def __repr__(self):
        return "GameMode('%s', %s)" % (self.name, self.has_teams)

class Round(object):

    """A Round represents a single round of play.

    .. attribute:: id
        The database ID of this Round

    .. attribute:: game_mode_name
        The name of this Round's GameMode

    .. attribute:: map_id
        The ID of this Round's Map

    .. attribute:: start_time
        A datetime representing the start of this Round

    .. attribute: end_time
        A datetime representing the end of this Round

    .. attribute:: players
        A list of this Round's Aliases

    .. attribute:: frags
        A list of this Round's Frags

    .. attribute:: flag_touches
        A list of this Round's FlagTouches

    .. attribute:: flag_returns
        A list of this Round's FlagReturns

    .. attribute:: rcon_accesses
        A list of this Round's RCONAccesses

    .. attribute:: rcon_denials
        A list of this Round's RCONDenials

    .. attribute:: rcon_actions
        A list of this Round's RCONActions

    """

    def __init__(self, game_mode=None, map=None, start_time=None):
        self.game_mode = game_mode
        self.map = map
        if game_mode:
            self.game_mode_name = game_mode.name
            if not self in self.game_mode.rounds:
                self.game_mode.rounds.append(self)
        if map:
            self.map_id = map.id
            if not self in self.map.rounds:
                self.map.rounds.append(self)
        if start_time:
            self.start_time = start_time

    def __str__(self):
        s = '<Round on %s at %s>'
        return s % (self.map, self.start_time)

    def __repr__(self):
        s = "Round(%s, %s)"
        return s % (self.map, self.start_time)

class StoredPlayer(object):

    """Represents a player.

    .. attribute:: name
        A string representing the name of this StoredPlayer

    .. attribute:: aliases
        A list of this StoredPlayer's Aliases

    """

    def __init__(self, name=None):
        self.name = name

    def __str__(self):
        return '<Player %s>' % (self.name)

    def __repr__(self):
        return "Player('%s')" % (self.name)

class Frag(object):

    """Represents a frag.

    .. attribute:: id
        The database ID of this Frag

    .. attribute:: fragger_id
        The database ID of this Frag's fragger (Alias)

    .. attribute:: fraggee_id
        The database ID of this Frag's fraggee (Alias)

    .. attribute:: weapon_name
        The name of this Frag's Weapon

    .. attribute:: round_id
        The database ID of this Frag's Round

    .. attribute:: timestamp
        A datetime representing the time at which this Frag occurred

    .. attribute:: fragger_was_holding_flag
        A boolean, whether or not the fragger was holding a flag

    .. attribute:: fraggee_was_holding_flag
        A boolean, whether or not the fraggee was holding a flag

    .. attribute:: fragger_team_color_name
        The name of fragger's TeamColor

    .. attribute:: fraggee_team_color_name
        The name of fraggee's TeamColor

    .. attribute:: red_team_holding_flag
        A boolean whether or not the red team was holding the flag

    .. attribute:: blue_team_holding_flag
        A boolean whether or not the blue team was holding the flag

    .. attribute:: green_team_holding_flag
        A boolean whether or not the green team was holding the flag

    .. attribute:: white_team_holding_flag
        A boolean whether or not the white team was holding the flag

    .. attribute:: red_team_score
        An int representing the red team's score

    .. attribute:: blue_team_score
        An int representing the blue team's score

    .. attribute:: green_team_score
        An int representing the green team's score

    .. attribute:: white_team_score
        An int representing the white team's score

    """

    def __init__(self, fragger=None, fraggee=None, weapon=None, round=None,
                       timestamp=None,
                       fragger_was_holding_flag=None,
                       fraggee_was_holding_flag=None,
                       fragger_team_color=None,
                       fraggee_team_color=None,
                       red_team_holding_flag=None,
                       blue_team_holding_flag=None,
                       green_team_holding_flag=None,
                       white_team_holding_flag=None,
                       red_team_score=None,
                       blue_team_score=None,
                       green_team_score=None,
                       white_team_score=None):
        self.fragger = fragger
        self.fraggee = fraggee
        self.weapon = weapon
        self.round = round
        self.fragger_team_color = fragger_team_color
        self.fraggee_team_color = fraggee_team_color
        if fragger:
            self.fragger_id = fragger.id
        if fraggee:
            self.fraggee_id = fraggee.id
        if weapon:
            self.weapon_name = weapon.name
        if round:
            self.round_id = round.id
        if fragger_team_color:
            self.fragger_team_color_name = fragger_team_color.color
        if fraggee_team_color:
            self.fraggee_team_color_name = fraggee_team_color.color
        if fragger and weapon and round:
            stuff = [x for x in [self.fragger, self.weapon, self.round] if x]
            if fraggee and fragger.id != fraggee.id:
                stuff.append(self.fraggee)
            if fragger_team_color:
                stuff.append(self.fragger_team_color)
                if fraggee_team_color and \
                   fragger_team_color.color != fraggee_team_color.color:
                    stuff.append(self.fraggee_team_color)
            for x in stuff:
                if self not in x.frags:
                    x.frags.append(self)
        self.timestamp = timestamp
        if fragger_was_holding_flag is not None:
            self.fragger_was_holding_flag = fragger_was_holding_flag
        if fraggee_was_holding_flag is not None:
            self.fraggee_was_holding_flag = fraggee_was_holding_flag
        if red_team_holding_flag is not None:
            self.red_team_holding_flag = red_team_holding_flag
        if blue_team_holding_flag is not None:
            self.blue_team_holding_flag = blue_team_holding_flag
        if green_team_holding_flag is not None:
            self.green_team_holding_flag = green_team_holding_flag
        if white_team_holding_flag is not None:
            self.white_team_holding_flag = white_team_holding_flag
        if red_team_score is not None:
            self.red_team_score = red_team_score
        if blue_team_score is not None:
            self.blue_team_score = blue_team_score
        if green_team_score is not None:
            self.green_team_score = green_team_score
        if white_team_score is not None:
            self.white_team_score = white_team_score

    def __str__(self):
        return '<Frag %s>' % (self.weapon)

class FlagTouch(object):

    """Represents a flag touch.

    .. attribute:: id
        The database ID of this FlagTouch

    .. attribute:: player_id
        The database ID of this FlagTouch's player (Alias)

    .. attribute:: round_id
        The database ID of this FlagTouch's Round

    .. attribute:: touch_time
        A datetime representing the time at which this FlagTouch
        began

    .. attribute:: loss_time
        A datetime representing the time at which this FlagTouch
        ended

    .. attribute:: was_picked
        A boolean, whether or not the flag was picked up (as opposed to
        taken from an enemy team's flag stand)

    .. attribute:: resulted_in_score
        A boolean, whether or not this FlagTouch ultimately resulted in
        a capture

    .. attribute:: player_team_color_name
        The name of player's TeamColor

    .. attribute:: red_team_holding_flag
        A boolean whether or not the red team was holding the flag

    .. attribute:: blue_team_holding_flag
        A boolean whether or not the blue team was holding the flag

    .. attribute:: green_team_holding_flag
        A boolean whether or not the green team was holding the flag

    .. attribute:: white_team_holding_flag
        A boolean whether or not the white team was holding the flag

    .. attribute:: red_team_score
        An int representing the red team's score

    .. attribute:: blue_team_score
        An int representing the blue team's score

    .. attribute:: green_team_score
        An int representing the green team's score

    .. attribute:: white_team_score
        An int representing the white team's score

    """

    def __init__(self, player=None, round=None, touch_time=None,
                       loss_time=None, was_picked=False,
                       resulted_in_score=False,
                       player_team_color=None,
                       red_team_holding_flag=False,
                       blue_team_holding_flag=False,
                       green_team_holding_flag=False,
                       white_team_holding_flag=False,
                       red_team_score=None,
                       blue_team_score=None,
                       green_team_score=None,
                       white_team_score=None):
        self.player = player
        self.round = round
        if player:
            self.player_id = player.id
            if self not in player.flag_touches:
                player.flag_touches.append(self)
        if round:
            self.round_id = round.id
            if self not in round.flag_touches:
                round.flag_touches.append(self)
        self.touch_time = touch_time
        if loss_time:
            self.loss_time = loss_time
        self.was_picked = was_picked
        self.resulted_in_score = resulted_in_score
        if player_team_color:
            self.player_team_color_name = player_team_color.color
        self.red_team_holding_flag = red_team_holding_flag
        self.blue_team_holding_flag = blue_team_holding_flag
        self.green_team_holding_flag = green_team_holding_flag
        self.white_team_holding_flag = white_team_holding_flag
        self.red_team_score = red_team_score
        self.blue_team_score = blue_team_score
        self.green_team_score = green_team_score
        self.white_team_score = white_team_score

    def __str__(self):
        return '<FlagTouch %s>' % (self.player)

class FlagReturn(object):

    """Represents a flag return.

    .. attribute:: id
        The database ID of this FlagReturn

    .. attribute:: player_id
        The database ID of this FlagReturn's player (Alias)

    .. attribute:: round_id
        The database ID of this FlagReturn's Round

    .. attribute:: timestamp
        A datetime representing the time at which this FlagReturn
        occurred

    .. attribute:: player_was_holding_flag
        A boolean, whether or not the returning player was holding a
        flag

    .. attribute:: player_team_color_name
        The name of player's TeamColor

    .. attribute:: red_team_holding_flag
        A boolean whether or not the red team was holding the flag

    .. attribute:: blue_team_holding_flag
        A boolean whether or not the blue team was holding the flag

    .. attribute:: green_team_holding_flag
        A boolean whether or not the green team was holding the flag

    .. attribute:: white_team_holding_flag
        A boolean whether or not the white team was holding the flag

    .. attribute:: red_team_score
        An int representing the red team's score

    .. attribute:: blue_team_score
        An int representing the blue team's score

    .. attribute:: green_team_score
        An int representing the green team's score

    .. attribute:: white_team_score
        An int representing the white team's score

    """

    def __init__(self, player=None, round=None, timestamp=None,
                       player_was_holding_flag=False,
                       player_team_color=None,
                       red_team_holding_flag=False,
                       blue_team_holding_flag=False,
                       green_team_holding_flag=False,
                       white_team_holding_flag=False,
                       red_team_score=None,
                       blue_team_score=None,
                       green_team_score=None,
                       white_team_score=None):
        self.player = player
        self.round = round
        if player:
            self.player_id = player.id
            if self not in player.flag_returns:
                player.flag_returns.append(self)
        if round:
            self.round_id = round.id
            if self not in round.flag_returns:
                round.flag_returns.append(self)
        self.timestamp = timestamp
        self.player_was_holding_flag = player_was_holding_flag
        if player_team_color:
            self.player_team_color_name = player_team_color.color
        self.red_team_holding_flag = red_team_holding_flag
        self.blue_team_holding_flag = blue_team_holding_flag
        self.green_team_holding_flag = green_team_holding_flag
        self.white_team_holding_flag = white_team_holding_flag
        self.red_team_score = red_team_score
        self.blue_team_score = blue_team_score
        self.green_team_score = green_team_score
        self.white_team_score = white_team_score

    def __str__(self):
        return '<FlagReturn %s>' % (self.player)

class RCONAccess(object):

    """Represents an RCON access.

    .. attribute:: id
        The database ID of this RCON access

    .. attribute:: player_id
        The database ID of this RCON access's player (Alias)

    .. attribute:: round_id
        The database ID of this RCON access's Round

    .. attribute:: timestamp
        A datetime representing the time at which this RCON access
        occurred

    """

    def __init__(self, player=None, round=None, timestamp=None):
        if player:
            self.player_id = player.id
            self.player = player
            if self not in self.player.rcon_accesses:
                self.player.rcon_accesses.append(self)
        if round:
            self.round_id = round.id
            self.round = round
            if self not in self.round.rcon_accesses:
                self.round.rcon_accesses.append(self)
        self.timestamp = timestamp

    def __str__(self):
        return '<RCON Access %s>' % (self.player)

class RCONDenial(object):

    """Represents an RCON denial.

    .. attribute:: id
        The database ID of this RCON denial

    .. attribute:: player_id
        The database ID of this RCON denial's player (Alias)

    .. attribute:: round_id
        The database ID of this RCON denial's Round

    .. attribute:: timestamp
        A datetime representing the time at which this RCON denial
        occurred

    """

    def __init__(self, player=None, round=None, timestamp=None):
        self.player = player
        self.round = round
        if player:
            self.player_id = player.id
            if self not in self.player.rcon_denials:
                self.player.rcon_denials.append(self)
        if round:
            self.round_id = round.id
            if self not in self.round.rcon_denials:
                self.round.rcon_denials.append(self)
        self.timestamp = timestamp

    def __str__(self):
        return '<RCON Denial %s>' % (self.player)

class RCONAction(object):

    """Represents an RCON action.

    .. attribute:: id
        The database ID of this RCON action

    .. attribute:: player_id
        The database ID of this RCON action's player (Alias)

    .. attribute:: round_id
        The database ID of this RCON action's Round

    .. attribute:: timestamp
        A datetime representing the time at which this RCON action
        occurred

    .. attribute:: action
        A string representing the name of the RCON action

    """

    def __init__(self, player=None, round=None, timestamp=None, action=None):
        self.player = player
        self.round = round
        if player:
            self.player_id = player.id
            if self not in self.player.rcon_actions:
                self.player.rcon_actions.append(self)
        if round:
            self.round_id = round.id
            if self not in self.round.rcon_actions:
                self.round.rcon_actions.append(self)
        self.timestamp = timestamp
        self.action = action

    def __str__(self):
        return '<RCON Action %s - %s>' % (self.action, self.player)

