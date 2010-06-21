from __future__ import with_statement

from sqlalchemy.orm.exc import NoResultFound

from ZDStack.Utils import parse_player_name
from ZDStack.ZDSDatabase import global_session
from ZDStack import get_engine, get_metadata
from ZDStack.ZDSTables import *

# zdslog = get_zdslog()

###
# Get the DB engine.
###
# zdslog.debug("Initializing Database")
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

    name = None
    ip_address = None
    was_namefake = None
    stored_player_name = None
    port = None
    number = None
    color = None
    playing = False
    disconnected = False

    def __init__(self, **kwargs):
        self.name = kwargs.get('name', None)
        self.ip_address = kwargs.get('ip_address', None)
        self.was_namefake = kwargs.get('was_namefake', None)
        self.stored_player_name = kwargs.get('stored_player_name', None)
        self.port = kwargs.get('port', None)
        self.number = kwargs.get('number', None)
        self.color = kwargs.get('color', None)
        self.playing = kwargs.get('playing', False)
        self.disconnected = kwargs.get('disconnected', False)

    def _get_ip(self):
        """Alias for ip_address"""
        return self.ip_address

    def _set_ip(self, ip):
        self.ip_address = ip

    def _del_ip(self):
        del self.ip_address

    ip = property(_get_ip, _set_ip, _del_ip)

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

    color = None

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

    name = None

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
        if not self.name:
            return u''
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
        if not sn:
            return u''
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

    wad_name = None
    number = None
    name = None

    def __init__(self, wad_name=None, number=None, name=None):
        self.wad_name = wad_name
        self.number = number
        self.name = name

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
        if self.wad and self.wad.short_name and self.wad.prefix and self.number:
            if u'DWANGO' in self.wad.short_name:
                return self.wad.prefix + u'M' + unicode(self.number)
            return self.wad.prefix + unicode(self.number).zfill(2)
        elif self.number:
            return u'MAP%s' % (unicode(self.number).zfill(2))
        else:
            return u''

class Weapon(object):

    """Weapon represents something that kills players.

    .. attribute:: name
        A string representing the name of the Weapon
    .. attribute:: is_suicide
        A boolean, whether or not the Weapon is a suicide
    .. attribute: frags
        A list of this Weapon's Frags

    """

    name = None
    is_suicide = None

    def __init__(self, name=None, is_suicide=None):
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

    name = None

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

    name = None
    has_teams = None

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

    game_mode_name = None
    map_id = None
    start_time = None
    end_time = None

    def __init__(self, game_mode_name=None, map_id=None, start_time=None, end_time=None):
        self.game_mode_name = game_mode_name
        self.map_id = map_id
        self.start_time = start_time
        self.end_time = end_time

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

    name = None

    def __init__(self, name=None):
        self.name = None

    def __str__(self):
        return '<Player %s>' % (self.name)

    def __repr__(self):
        return "Player('%s')" % (self.name)

    @property
    def rounds(self):
        out = set()
        for alias in self.aliases:
            for round in alias.rounds:
                out.add(round)
        return list(out)

    @property
    def frags(self):
        out = set()
        for round in self.rounds:
            for frag in round.frags:
                if frag.fragger in self.aliases and \
                   frag.fragger_id != frag.fraggee_id:
                    out.add(frag)
        return list(out)

    @property
    def deaths(self):
        out = set()
        for round in self.rounds:
            for frag in round.frags:
                if frag.fraggee in self.aliases:
                    out.add(frag)
        return list(out)

    @property
    def suicides(self):
        return [x for x in deaths if x.fragger_id == x.fraggee_id]

    @property
    def flag_touches(self):
        out = set()
        for round in self.rounds:
            for flag_touch in round.flag_touches:
                out.add(flag_touch)
        return list(out)

    @property
    def flag_captures(self):
        return [x for x in self.flag_touches if x.resulted_in_score]

    @property
    def flag_returns(self):
        out = set()
        for round in self.rounds:
            for flag_return in round.flag_returns:
                out.add(flag_return)
        return list(out)

    @property
    def rcon_accesses(self):
        out = set()
        for round in self.rounds:
            for rcon_access in round.rcon_accesses:
                out.add(rcon_access)
        return list(out)

    @property
    def rcon_denials(self):
        out = set()
        for round in self.rounds:
            for rcon_denial in round.rcon_denials:
                out.add(rcon_denial)
        return list(out)

    @property
    def rcon_actions(self):
        out = set()
        for round in self.rounds:
            for rcon_action in round.rcon_actions:
                out.add(rcon_action)
        return list(out)

    # rounds = association_proxy('aliases', 'rounds')
    # frags = association_proxy('aliases', 'frags')

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

    fragger_id = None
    fraggee_id = None
    weapon_name = None
    round_id = None
    timestamp = None
    fragger_was_holding_flag = None
    fraggee_was_holding_flag = None
    fragger_team_color_name = None
    fraggee_team_color_name = None
    red_team_holding_flag = None
    blue_team_holding_flag = None
    green_team_holding_flag = None
    white_team_holding_flag = None
    red_team_score = None
    blue_team_score = None
    green_team_score = None
    white_team_score = None

    def __init__(self, **kwargs):
        self.fragger_id = kwargs.get('fragger_id', None)
        self.fraggee_id = kwargs.get('fraggee_id', None)
        self.weapon_name = kwargs.get('weapon_name', None)
        self.round_id = kwargs.get('round_id', None)
        self.timestamp = kwargs.get('timestamp', None)
        self.fragger_was_holding_flag = \
                kwargs.get('fragger_was_holding_flag', None)
        self.fraggee_was_holding_flag = \
                kwargs.get('fraggee_was_holding_flag', None)
        self.fragger_team_color_name = \
                kwargs.get('fragger_team_color_name', None)
        self.fraggee_team_color_name = \
                kwargs.get('fraggee_team_color_name', None)
        self.red_team_holding_flag = kwargs.get('red_team_holding_flag', None)
        self.blue_team_holding_flag = \
                kwargs.get('blue_team_holding_flag', None)
        self.green_team_holding_flag = \
                kwargs.get('green_team_holding_flag', None)
        self.white_team_holding_flag = \
                kwargs.get('white_team_holding_flag', None)
        self.red_team_score = kwargs.get('red_team_score', None)
        self.blue_team_score = kwargs.get('blue_team_score', None)
        self.green_team_score = kwargs.get('green_team_score', None)
        self.white_team_score = kwargs.get('white_team_score', None)

    def __str__(self):
        return '<Frag %s>' % (self.weapon)

class FlagTouch(object):

    """Represents a flag touch.

    .. attribute:: id
        The database ID of this FlagTouch

    .. attribute:: alias_id
        The database ID of this FlagTouch's alias

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

    player_id = None
    round_id = None
    touch_time = None
    loss_time = None
    was_picked = None
    resulted_in_score = None
    player_team_color_name = None
    red_team_holding_flag = None
    blue_team_holding_flag = None
    green_team_holding_flag = None
    white_team_holding_flag = None
    red_team_score = None
    blue_team_score = None
    green_team_score = None
    white_team_score = None

    def __init__(self, **kwargs):
        self.player_id = kwargs.get('player_id', None)
        self.round_id = kwargs.get('round_id', None)
        self.touch_time = kwargs.get('touch_time', None)
        self.loss_time = kwargs.get('touch_time', None)
        self.was_picked = kwargs.get('was_picked', None)
        self.resulted_in_score = kwargs.get('resulted_in_score', None)
        self.player_team_color_name = \
                kwargs.get('player_team_color_name', None)
        self.red_team_holding_flag = kwargs.get('red_team_holding_flag', None)
        self.blue_team_holding_flag = \
                kwargs.get('blue_team_holding_flag', None)
        self.green_team_holding_flag = \
                kwargs.get('green_team_holding_flag', None)
        self.white_team_holding_flag = \
                kwargs.get('white_team_holding_flag', None)
        self.red_team_score = kwargs.get('red_team_score', None)
        self.blue_team_score = kwargs.get('blue_team_score', None)
        self.green_team_score = kwargs.get('green_team_score', None)
        self.white_team_score = kwargs.get('white_team_score', None)

    def __str__(self):
        return '<FlagTouch %s>' % (self.alias)

class FlagReturn(object):

    """Represents a flag return.

    .. attribute:: id
        The database ID of this FlagReturn

    .. attribute:: alias_id
        The database ID of this FlagReturn's alias

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

    player_id = None
    round_id = None
    timestamp = None
    player_was_holding_flag = None
    player_team_color_name = None
    red_team_holding_flag = None
    blue_team_holding_flag = None
    green_team_holding_flag = None
    white_team_holding_flag = None
    red_team_score = None
    blue_team_score = None
    green_team_score = None
    white_team_score = None

    def __init__(self, **kwargs):
        self.player_id = kwargs.get('player_id', None)
        self.round_id = kwargs.get('round_id', None)
        self.timestamp = kwargs.get('timestamp', None)
        self.player_was_holding_flag = kwargs.get('player_was_holding_flag', None)
        self.resulted_in_score = kwargs.get('resulted_in_score', None)
        self.player_team_color_name = \
                kwargs.get('player_team_color_name', None)
        self.red_team_holding_flag = kwargs.get('red_team_holding_flag', None)
        self.blue_team_holding_flag = \
                kwargs.get('blue_team_holding_flag', None)
        self.green_team_holding_flag = \
                kwargs.get('green_team_holding_flag', None)
        self.white_team_holding_flag = \
                kwargs.get('white_team_holding_flag', None)
        self.red_team_score = kwargs.get('red_team_score', None)
        self.blue_team_score = kwargs.get('blue_team_score', None)
        self.green_team_score = kwargs.get('green_team_score', None)
        self.white_team_score = kwargs.get('white_team_score', None)

    def __str__(self):
        return '<FlagReturn %s>' % (self.alias)

class RCONAccess(object):

    """Represents an RCON access.

    .. attribute:: id
        The database ID of this RCON access

    .. attribute:: alias_id
        The database ID of this RCON access's alias

    .. attribute:: round_id
        The database ID of this RCON access's Round

    .. attribute:: timestamp
        A datetime representing the time at which this RCON access
        occurred

    """

    player_id = None
    round_id = None
    timestamp = None

    def __init__(self, **kwargs):
        self.player_id = kwargs.get('player_id', None)
        self.round_id = kwargs.get('round_id', None)
        self.timestamp = kwargs.get('timestamp', None)

    def __str__(self):
        return '<RCON Access %s>' % (self.alias)

class RCONDenial(object):

    """Represents an RCON denial.

    .. attribute:: id
        The database ID of this RCON denial

    .. attribute:: alias_id
        The database ID of this RCON denial's alias

    .. attribute:: round_id
        The database ID of this RCON denial's Round

    .. attribute:: timestamp
        A datetime representing the time at which this RCON denial
        occurred

    """

    player_id = None
    round_id = None
    timestamp = None

    def __init__(self, **kwargs):
        self.player_id = kwargs.get('player_id', None)
        self.round_id = kwargs.get('round_id', None)
        self.timestamp = kwargs.get('timestamp', None)

    def __str__(self):
        return '<RCON Denial %s>' % (self.alias)

class RCONAction(object):

    """Represents an RCON action.

    .. attribute:: id
        The database ID of this RCON action

    .. attribute:: alias_id
        The database ID of this RCON action's alias

    .. attribute:: round_id
        The database ID of this RCON action's Round

    .. attribute:: timestamp
        A datetime representing the time at which this RCON action
        occurred

    .. attribute:: action
        A string representing the name of the RCON action

    """

    player_id = None
    round_id = None
    timestamp = None
    action = None

    def __init__(self, **kwargs):
        self.player_id = kwargs.get('player_id', None)
        self.round_id = kwargs.get('round_id', None)
        self.timestamp = kwargs.get('timestamp', None)

    def __str__(self):
        return '<RCON Action %s - %s>' % (self.action, self.alias)

class RoundsAndAliases(object): pass

