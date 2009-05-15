from __future__ import with_statement

import os.path

from decimal import Decimal
from threading import Lock

from ConfigParser import RawConfigParser as RCP
from ConfigParser import SafeConfigParser as SCP
from ConfigParser import DEFAULTSECT, NoSectionError, NoOptionError

from ZDStack.Utils import resolve_path, requires_instance_lock
from ZDStack.ZDSFile import SynchronizedFile

class RawZDSConfigParser(SynchronizedFile, RCP):

    """RawZDSConfigParser improves on ConfigParser.RawConfigParser.

    The following improvements are made:

      * All operations are threadsafe.
      * the internal dict of defaults is never returned
      * get() and get*() methods can handle default arguments.
      * getdecimal(), getlist() and getpath() methods were added
      * section order is preserved
      * read/readfp were replaced by load and loadfp
      * reload/reloadfp/save methods were also added

    Regarding get*() methods and defaults, passing 'None' (or nothing)
    as the 'default' argument causes the 'NoOptionError' to be raised
    if an option is not found.  This is also the default behavior.

    .. attribute:: _section_list
        A list of section names, used to keep sections in order when
        writing the configuration to disk

    .. attribute:: lock
        A Lock that must be acquired before using the ConfigParser

    .. attribute:: dummy
        A boolean, whether or not the ConfigParser is a dummy and
        therefore shouldn't perform checks on the underlying file
    
    """

    def __init__(self, filename=None, dummy=False):
        """Initializes a RawZDSConfigParser."""
        self._section_list = []
        RCP.__init__(self)
        SynchronizedFile.__init__(self, filename, dummy)

    @requires_instance_lock()
    def defaults(self):
        return dict(RCP.defaults(self).items())

    @requires_instance_lock()
    def sections(self):
        return [x for x in self._section_list]

    @requires_instance_lock()
    def add_section(self, section):
        """Adds a section.

        :param section: the name of the new section
        :type section: string

        """
        RCP.add_section(self, section)
        self._section_list.append(section)

    @requires_instance_lock()
    def has_section(self, section):
        """Tests if a section exists or not.

        :param section: the name of the section to test for
        :type section: string
        :rtype: boolean
        :returns: a boolean whether the section exists or not

        """
        return section in self._section_list

    @requires_instance_lock()
    def options(self, section):
        """Returns a section's options.

        :param section: the name of the section whose options are to
                        be returned
        :type section: string
        :rtype: list of strings
        :returns: a list of strings representing the names of the
                  options

        """
        return RCP.options(self, section)

    def read(self, filenames):
        """Old 'read' method from ConfigParser.

        :param filenames: the names of the files to parse
        :type filenames: list of strings

        This method will raise an Exception if used, the
        ZDSConfigParsers are designed to be used with one file only.
        Typically the "read a bunch of files for data" method was only
        useful when checking a prioritized list of possible config
        files, but ZDStack already does this in __init__, so this
        method has become useless.

        """
        raise Exception("Don't use this method")

    def readfp(self, fp, filename=None):
        """Old 'readfp' method from ConfigParser.

        :param fp: a file object whose contents are to be parsed
        :type fp: file

        For the same reasons 'read' is useless, this method is also
        useless and will also raise an Exception if used.

        """
        raise Exception("Don't use this method")

    @requires_instance_lock()
    def get_excluding_defaults(self, section, option, default=None):
        """Gets an option's value.

        :param section: the name of the section in which to look for
                        the option
        :type section: string
        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: string
        :returns: the string value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.  This method
                  also excludes the DEFAULT section.

        """
        opt = self.optionxform(option)
        if not self.has_section(section, acquire_lock=False):
            raise NoSectionError(section)
        if opt in self._sections[section]:
            return self._sections[section][opt]
        elif default is not None:
            return default
        else:
            raise NoOptionError(section, opt)

    @requires_instance_lock()
    def get(self, section, option, default=None):
        """Gets an option's value.

        :param section: the name of the section in which to look for
                        the option
        :type section: string
        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: string
        :returns: the string value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
        opt = self.optionxform(option)
        if section in self._sections:
            if opt in self._sections[section]:
                return self._sections[section][opt]
            elif opt in self._defaults:
                return self._defaults[opt]
            elif default is not None:
                return default
            else:
                raise NoOptionError(section, option)
        elif section != DEFAULTSECT:
            raise NoSectionError(section)
        elif opt in self._defaults:
            return self._defaults[opt]
        elif default is not None:
            return default
        else:
            raise NoOptionError(section, option)

    @requires_instance_lock()
    def items(self, section):
        """Gets a section's items.

        :param section: the name of the section whose items are to be
                        returned
        :type section: string
        :rtype: list of 2-Tuples
        :returns: a list of a section's options and values, i.e.
                  [('option', 'value1'), ('option2', 'value2')]

        """
        return RCP.items(self, section)

    @requires_instance_lock()
    def _get(self, section, conv, option, default=None):
        return conv(self.get(section, option, default, acquire_lock=False))

    @requires_instance_lock()
    def getint(self, section, option, default=None):
        """Gets an option's value as an int.

        :param section: the name of the section in which to look for
                        the option
        :type section: string
        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: int
        :returns: the int value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
        return self._get(section, int, option, default, acquire_lock=False)

    @requires_instance_lock()
    def getfloat(self, section, option, default=None):
        """Gets an option's value as a float.

        :param section: the name of the section in which to look for
                        the option
        :type section: string
        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: float
        :returns: the float value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
        return self._get(section, float, option, default, acquire_lock=False)

    @requires_instance_lock()
    def getdecimal(self, section, option, default=None):
        """Gets an option's value as a Decimal.

        :param section: the name of the section in which to look for
                        the option
        :type section: string
        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: Decimal
        :returns: the Decimal value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
        return self._get(section, Decimal, option, default, acquire_lock=False)

    @requires_instance_lock()
    def getlist(self, section, option, default=None, parse_func=None):
        """Gets an option's value as a list.

        :param section: the name of the section in which to look for
                        the option
        :type section: string
        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :param parse_func: a function used to parse the option's value
                           into a list.  optional, the default is:
                           'lambda x: [y.strip() for y in x.split(',')]'
        :type parse_func: function
        :rtype: list
        :returns: the parsed list value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
        if not parse_func:
            parse_func = lambda x: [y.strip() for y in x.split(',')]
        return self._get(section, parse_func, option, default,
                         acquire_lock=False)

    _boolean_states = RCP._boolean_states

    for state in ('y', 't', 'absolutely', "can't live without it", 'god yes',
                  'jesus christ yes', 'jesus yes', 'fuck yes', 'fuck yeah',
                  'shit yes', 'shit yeah', 'obviously', 'always',
                  'i would probably kill myself without this'):
        _boolean_states[state] = True

    for state in ('n', 'f', 'never', 'god no', 'jesus no', 'jesus christ no',
                  'jesus are you joking?', 'jesus are you kidding?',
                  'jesus are you serious?', 'jesus christ are you joking?',
                  'jesus christ are you kidding?',
                  'jesus christ are you serious?', 'fuck no', 'shit no',
                  'oh man not a chance'
                  'i would probably kill myself if i had to put up with this',
                  'no way', 'no way jose', 'not a chance', 'definitely not'):
        _boolean_states[state] = False

    @requires_instance_lock()
    def getboolean(self, section, option, default=None):
        """Gets an option's value as a boolean.

        :param section: the name of the section in which to look for
                        the option
        :type section: string
        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: boolean
        :returns: the boolean value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
        v = self.get(section, option, default, acquire_lock=False)
        lv = v.lower()
        if lv not in self._boolean_states:
            raise ValueError("Not a boolean: %s" % (v))
        return self._boolean_states[lv]

    @requires_instance_lock()
    def getpath(self, section, option, default=None):
        """Gets an option's value as a resolved path.

        :param section: the name of the section in which to look for
                        the option
        :type section: string
        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: string
        :returns: the string value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.  The value will
                  be passed through
                  os.path.abspath(os.path.expanduser(v)).

        """
        return self._get(section, resolve_path, option, default,
                         acquire_lock=False)

    @requires_instance_lock()
    def has_option(self, section, option):
        """Checks if a section contains a specified option.

        :param section: the name of the section to be checked
        :type section: string
        :param option: the option to check for
        :type option: string
        :rtype: boolean

        """
        return RCP.has_option(self, section, option)

    @requires_instance_lock()
    def set(self, section, option, value):
        """Sets a section's option to 'value'.

        :param section: the name of the section whose option's value
                        is to be set
        :type section: string
        :param option: the option whose value is to be set
        :type option: string
        :param value: the new value of the option
        :type value: string

        """
        RCP.set(self, section, option, value)

    def __str__(self):
        out = ''
        sect_temp = "[%s]\n"
        opt_temp = "%s = %s\n"
        if self._defaults:
            out += sect_temp % DEFAULTSECT
            for k in sorted(self._defaults.keys()):
                v = str(self._defaults[k]).replace('\n', '\n\t')
                out += opt_temp % (k, v)
            out += "\n"
        for section in self._section_list:
            out += sect_temp % section
            for k in sorted(self._sections[section].keys()):
                if k != "__name__" and k != 'name':
                    v = str(self._sections[section][k]).replace('\n', '\n\t')
                    out += opt_temp % (k, v)
            out += "\n"
        return out

    @requires_instance_lock()
    def remove_option(self, section, option):
        """Removes an option from a section.

        :param section: the section from which to remove the option
        :type section: string
        :param option: the option to be removed
        :type option: string
        :rtype: boolean
        :returns: True if the option existed

        """
        return RCP.remove_option(self, section, option)

    @requires_instance_lock()
    def remove_section(self, section):
        """Removes a section.

        :param section: the section to be removed
        :type section: string
        :rtype: boolean
        :returns: True if the section existed

        """
        if RCP.remove_section(self, section):
            self._section_list.remove(section)
            return True
        return False

    @requires_instance_lock()
    def clear(self):
        """Removes all sections, including the DEFAULT section."""
        for s in self.sections(acquire_lock=False) + [DEFAULTSECT]:
            self.remove_section(s, acquire_lock=False)

    @requires_instance_lock()
    def get_if_valid(self, section, option):
        """Gets an option's value if it is defined and non-False.

        :param section: the name of the section in which to look for
                        the option
        :type section: string
        :param option: the name of the option to look for
        :type option: string
        :returns: the option's value if it is defined and non-False.
                  Otherwise returns None.

        """
        try:
            val = self.get(section, option, acquire_lock=False)
            if not val:
                return None
        except NoOptionError:
            return None

    @requires_instance_lock()
    def get_if_true(self, section, option):
        """Gets an option's value if it is defined and True.

        :param section: the name of the section in which to look for
                        the option
        :type section: string
        :param option: the name of the option to look for
        :type option: string
        :returns: the option's value if it is defined and True.
                  Otherwise returns None.

        """
        try:
            return self.getboolean(section, option, acquire_lock=False)
        except NoOptionError:
            return None

    def _read(self, fp, fpname):
        """Parse a sectioned setup file.

        The sections in setup file contains a title line at the top,
        indicated by a name in square brackets (`[]'), plus key/value
        options lines, indicated by `name: value' format lines.
        Continuations are represented by an embedded newline then
        leading whitespace.  Blank lines, lines beginning with a '#',
        and just about everything else are ignored.
        """
        cursect = None                            # None, or a dictionary
        optname = None
        lineno = 0
        e = None                                  # None, or an exception
        while True:
            line = fp.readline()
            if not line:
                break
            lineno = lineno + 1
            # comment or blank line?
            if line.strip() == '' or line[0] in '#;':
                continue
            if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
                # no leading whitespace
                continue
            # continuation line?
            if line[0].isspace() and cursect is not None and optname:
                value = line.strip()
                if value:
                    cursect[optname] = "%s\n%s" % (cursect[optname], value)
            # a section header or option header?
            else:
                # is it a section header?
                mo = self.SECTCRE.match(line)
                if mo:
                    sectname = mo.group('header')
                    if sectname in self._sections:
                        cursect = self._sections[sectname]
                    elif sectname == DEFAULTSECT:
                        cursect = self._defaults
                    else:
                        cursect = {'__name__': sectname}
                        self._section_list.append(sectname)
                        self._sections[sectname] = cursect
                    # So sections can't start with a continuation line
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    raise MissingSectionHeaderError(fpname, lineno, line)
                # an option line?
                else:
                    mo = self.OPTCRE.match(line)
                    if mo:
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        if vi in ('=', ':') and ';' in optval:
                            # ';' is a comment delimiter only if it follows
                            # a spacing character
                            pos = optval.find(';')
                            if pos != -1 and optval[pos-1].isspace():
                                optval = optval[:pos]
                        optval = optval.strip()
                        # allow empty values
                        if optval == '""':
                            optval = ''
                        optname = self.optionxform(optname.rstrip())
                        cursect[optname] = optval
                    else:
                        # a non-fatal parsing error occurred.  set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        if not e:
                            e = ParsingError(fpname)
                        e.append(lineno, repr(line))
        # if any parsing errors occurred, raise an exception
        if e:
            raise e

class ZDSConfigParser(RawZDSConfigParser, SCP):

    """ZDSConfigParser is RawZDSConfigParser with magic interpolation.
    
    .. attribute:: _section_list
        A list of section names, used to keep sections in order when
        writing the configuration to disk
    .. attribute:: lock
        A Lock that must be acquired before using the ConfigParser
    .. attribute:: dummy
        A boolean, whether or not the ConfigParser is a dummy and
        therefore shouldn't perform checks on the underlying file
    
    All interpolation is done with SafeConfigParser's methods, so
    interpolation shouldn't get out of control.
    
    """

    def __init__(self, filename=None):
        SCP.__init__(self)
        RawZDSConfigParser.__init__(self, filename)

    @requires_instance_lock()
    def get_raw(self, section, option, default=None):
        """Gets an option's value without interpolation.

        :param section: the name of the section in which to look for
                        the option
        :type section: string
        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :rtype: string
        :returns: the string value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
        return RawZDSConfigParser.get(self, section, option, default,
                                      acquire_lock=False)

    @requires_instance_lock()
    def get(self, section, option, default=None, raw=False, vars=None):
        """Gets an option's value without interpolation.

        :param section: the name of the section in which to look for
                        the option
        :type section: string
        :param option: the name of the option whose value is to be
                       returned
        :type option: string
        :param default: optional, a value to be returned if the option
                        if not found
        :param raw: whether or not to return the raw value of the
                    option, with no interpolation.  False by default.
        :type raw: boolean
        :param vars: additional values to be used during interpolation
        :type vars: dict
        :rtype: string
        :returns: the string value of the option if found.  If the
                  option is not found, but 'default' is not None,
                  the value of the 'default' argument will be returned.
                  Otherwise a NoOptionError is raised.

        """
        ###
        # Get the option value to be interpolated.
        ###
        rawval = self.get_raw(section, option, default, acquire_lock=False)
        if raw:
            ###
            # Don't do all this crap if we're just gonna return the
            # regular 'ol value.
            ###
            return rawval
        ###
        # The first step is to get all the interpolation values
        # into a dict, even if they may need to be interpolated as well.
        ###
        d = self._defaults.copy()
        try:
            d.update(self._sections[section])
        except KeyError:
            if section != DEFAULTSECT:
                raise NoSectionError(section)
        ###
        # There might be specific variables set, so add those too.
        ###
        if vars:
            for key, value in vars.items():
                d[self.optionxform(key)] = value
        option = self.optionxform(option)
        ###
        # Finally, try and interpolate this mofkr.
        ###
        return self._interpolate(section, option, rawval, d)

    @requires_instance_lock()
    def items(self, section, raw=False, vars=None):
        """Returns a section's items.

        :param section: the name of the section whose items are to be
                        returned
        :type section: string
        :param raw: whether or not to return the raw value of the
                    option, with no interpolation.  False by default.
        :type raw: boolean
        :param vars: additional values to be used during interpolation
        :type vars: dict
        :rtype: list of 2-Tuples
        :returns: a list of a section's options and values, i.e.
                  [('option', 'value1'), ('option2', 'value2')]

        """
        return SCP.items(self, section, raw, vars)

    @requires_instance_lock()
    def set(self, section, option, value):
        """Sets a section's option to 'value'.

        :param section: the name of the section whose option's value
                        is to be set
        :type section: string
        :param option: the option whose value is to be set
        :type option: string
        :param value: the new value of the option
        :type value: string

        """
        return SCP.set(self, section, option, value)

