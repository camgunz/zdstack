from __future__ import with_statement

import os.path

from decimal import Decimal
from threading import Lock

from ConfigParser import RawConfigParser as RCP
from ConfigParser import SafeConfigParser as SCP
from ConfigParser import DEFAULTSECT, NoSectionError, NoOptionError

from ZDStack.Utils import resolve_path, requires_instance_lock

class RawZDSConfigParser(RCP):

    """RawZDSConfigParser improves on ConfigParser.RawConfigParser.

    The following improvements are made:

      - All operations are threadsafe.
      - the internal dict of defaults is never returned
      - get() and get*() methods can handle default arguments.
      - getdecimal(), getlist() and getpath() methods were added
      - section order is preserved
      - read/readfp were replaced by load and loadfp
      - reload/reloadfp/save methods were also added

    Regarding get*() methods and defaults, passing 'None' (or nothing)
    as the 'default' argument causes the 'NoOptionError' to be raised
    if an option is not found.
    
    """

    def __init__(self, filename=None, dummy=False):
        """Initializes a RawZDSConfigParser.

        filename:                 a string representing the name of a
                                  a file to parse initially
        dummy:                    a boolean that, if given, won't
                                  perform checks on the underlying
                                  file.

        All arguments are optional.

        """
        RCP.__init__(self)
        self._section_list = []
        self.lock = Lock()
        self.dummy = dummy
        if filename:
            if isinstance(filename, str):
                self.set_file(filename)
                self.load()
            elif hasattr(filename, 'readline'):
                if not self.dummy:
                    if not hasattr(filename, 'name'):
                        es = "Given file objects must have a 'name' attribute"
                        raise ValueError(es)
                    self.set_file(filename.name)
                self.loadfp(filename)
            else:
                es = "Unsupported type for 'filename': [%s]"
                raise ValueError(es % (type(filename)))

    @requires_instance_lock()
    def set_file(self, filename):
        """Sets the location of the configuration file.

        filename:     a string representing the new location of the
                      configuration file

        """
        if self.dummy:
            return
        f = resolve_path(filename)
        if not os.path.isfile(f):
            raise ValueError("Config File [%s] not found" % (filename))
        self.filename = f

    @requires_instance_lock()
    def defaults(self):
        return dict(RCP.defaults(self).items())

    @requires_instance_lock()
    def sections(self):
        return [x for x in self._section_list]

    @requires_instance_lock()
    def add_section(self, section):
        RCP.add_section(self, section)
        self._section_list.append(section)

    @requires_instance_lock()
    def has_section(self, section):
        return section in self._section_list

    @requires_instance_lock()
    def options(self, section):
        return RCP.options(self, section)

    def read(self, filenames):
        raise Exception("Don't use this method")

    def readfp(self, fp, filename=None):
        raise Exception("Don't use this method")

    @requires_instance_lock()
    def get(self, section, option, default=None):
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
        return RCP.items(self, section)

    @requires_instance_lock()
    def _get(self, section, conv, option, default=None):
        return conv(self.get(section, option, default, acquire_lock=False))

    @requires_instance_lock()
    def getint(self, section, option, default=None):
        return self._get(section, int, option, default, acquire_lock=False)

    @requires_instance_lock()
    def getfloat(self, section, option, default=None):
        return self._get(section, float, option, default, acquire_lock=False)

    @requires_instance_lock()
    def getdecimal(self, section, option, default=None):
        return self._get(section, Decimal, option, default, acquire_lock=False)

    @requires_instance_lock()
    def getlist(self, section, option, default=None, parse_func=None):
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
        v = self.get(section, option, default, acquire_lock=False)
        lv = v.lower()
        if lv not in self._boolean_states:
            raise ValueError("Not a boolean: %s" % (v))
        return self._boolean_states[lv]

    @requires_instance_lock()
    def getpath(self, section, option, default=None):
        return self._get(section, resolve_path, option, default,
                         acquire_lock=False)

    @requires_instance_lock()
    def has_option(self, section, option):
        return RCP.has_option(self, section, option)

    @requires_instance_lock()
    def set(self, section, option, value):
        RCP.set(self, section, option, value)

    @requires_instance_lock()
    def write(self, fp):
        if self._defaults:
            fp.write("[%s]\n" % DEFAULTSECT)
            for (key, value) in self._defaults.items():
                s = "%s = %s\n"
                fp.write(s % (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")
        for section in self._section_list:
            fp.write("[%s]\n" % section)
            for (key, value) in self._sections[section].items():
                if key != "__name__":
                    fp.write("%s = %s\n" %
                             (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")

    @requires_instance_lock()
    def remove_option(self, section, option):
        return RCP.remove_option(self, section, option)

    @requires_instance_lock()
    def remove_section(self, section):
        if RCP.remove_section(self, section):
            self._section_list.remove(section)
            return True
        return False

    @requires_instance_lock()
    def clear(self):
        """Removes all sections, including the DEFAULT section."""
        sections = self.sections(acquire_lock=False) + [DEFAULTSECT]
        for s in sections:
            self.remove_section(s, acquire_lock=False)

    @requires_instance_lock()
    def load(self):
        """Loads the data from the configuration file."""
        if self.dummy:
            raise Exception("Can't load() a dummy configparser")
        self._read(open(self.filename), self.filename)

    @requires_instance_lock()
    def loadfp(self, fobj):
        """Loads configuration data from a file object.
        
        fobj:         a file object containing configuration data

        This BCP's filename will also be set to the resolved value of
        the file object's .name attribute, so the passed file object
        must have a .name attribute.
        
        """
        if not self.dummy:
            if not hasattr(fobj, 'name'):
                es = "File objects passed to loadfp must have a .name "
                es += "attribute"
                raise ValueError(es)
            self.set_file(fobj.name, acquire_lock=False)
        if self.dummy:
            filename = '<???>' # Haha, I used to hate this
        else:
            filename = self.filename
        self._read(fobj, filename)

    @requires_instance_lock()
    def reload(self):
        """Reloads configuration data from the configuration file."""
        self.clear(acquire_lock=False)
        self.load(acquire_lock=False)

    @requires_instance_lock()
    def reloadfp(self, fobj):
        """Reloads configuration data from a file object.

        fobj: a file object containing configuration data

        This BCP's filename will also be set to the resolved value of
        the file object's .name attribute, so the passed file object
        must have a .name attribute.
        
        """
        self.clear(acquire_lock=False)
        self.loadfp(fobj, acquire_lock=False)

    @requires_instance_lock()
    def save(self):
        """Writes configuration data to the configuration file."""
        fobj = open(self.filename, 'w')
        try:
            self.write(fobj, acquire_lock=False)
            fobj.flush()
        finally:
            fobj.close()

    @requires_instance_lock()
    def get_if_valid(self, section, option):
        try:
            val = self.get(section, option, acquire_lock=False)
            if not val:
                return None
        except NoOptionError:
            return None

    @requires_instance_lock()
    def get_if_true(self, section, option):
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
    
    All interpolation is done with SafeConfigParser's methods, so
    things shouldn't get out of control.
    
    """

    def __init__(self, filename=None):
        SCP.__init__(self)
        RawZDSConfigParser.__init__(self, filename)

    @requires_instance_lock()
    def get_raw(self, section, option, default=None):
        return RawZDSConfigParser.get(self, section, option, default,
                                      acquire_lock=False)

    @requires_instance_lock()
    def get(self, section, option, default=None, raw=False, vars=None):
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
        return SCP.items(self, section, raw, vars)

    @requires_instance_lock()
    def set(self, section, option, value):
        return SCP.set(self, section, option, value)

