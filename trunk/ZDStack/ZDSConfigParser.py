from __future__ import with_statement

import os.path
import logging

from decimal import Decimal
from threading import Lock

from ConfigParser import RawConfigParser as RCP
from ConfigParser import SafeConfigParser as SCP
from ConfigParser import DEFAULTSECT, NoSectionError, NoOptionError

from ZDStack.Utils import resolve_path

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
        """Initializes a BaseConfigParser.

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

    def set_file(self, filename, acquire_lock=True):
        """Sets the location of the configuration file.

        filename:     a string representing the new location of the
                      configuration file
        acquire_lock: a boolean that, if True, will acquire this BCP's
                      lock before setting the file.  True by default.

        """
        def blah():
            if self.dummy:
                return
            f = resolve_path(filename)
            logging.debug("Setting Configuration File: [%s]" % (f))
            if not os.path.isfile(f):
                raise ValueError("Config File [%s] not found" % (filename))
            self.filename = f
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def defaults(self, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                return dict(RCP.defaults(self).items())
        else:
            return dict(RCP.defaults(self).items())

    def sections(self, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                return [x for x in self._section_list]
        else:
            return [x for x in self._section_list]

    def add_section(self, section, acquire_lock=True):
        def blah():
            RCP.add_section(self, section)
            self._section_list.append(section)
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def has_section(self, section, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                return section in self._section_list
        else:
            return section in self._section_list

    def options(self, section, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                return RCP.options(self, section)
        else:
            return RCP.options(self, section)

    def read(self, filenames, acquire_lock=True):
        raise Exception("Don't use this method")

    def readfp(self, fp, filename=None):
        raise Exception("Don't use this method")

    def get(self, section, option, default=None, acquire_lock=True):
        def blah():
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
        if acquire_lock:
            with self.lock:
                return blah()
        else:
            return blah()

    def items(self, section, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                return RCP.items(self, section)
        else:
            return RCP.items(self, section)

    def _get(self, section, conv, option, default=None, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                return conv(self.get(section, option, default,
                                     acquire_lock=False))
        else:
            return conv(self.get(section, option, default, acquire_lock=False))

    def getint(self, section, option, default=None, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                return self._get(section, int, option, default,
                                 acquire_lock=False)
        else:
            return self._get(section, int, option, default,
                             acquire_lock=False)

    def getfloat(self, section, option, default=None, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                return self._get(section, float, option, default,
                                 acquire_lock=False)
        else:
            return self._get(section, float, option, default,
                             acquire_lock=False)

    def getdecimal(self, section, option, default=None, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                return self._get(section, Decimal, option, default,
                                 acquire_lock=False)
        else:
            return self._get(section, Decimal, option, default,
                             acquire_lock=False)

    def getlist(self, section, option, default=None, parse_func=None,
                                                     acquire_lock=True):
        if not parse_func:
            parse_func = lambda x: [y.strip() for y in x.split(',')]
        if acquire_lock:
            with self.lock:
                return self._get(section, parse_func, option, default,
                                 acquire_lock=False)
        else:
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

    def getboolean(self, section, option, default=None, acquire_lock=True):
        def blah():
            v = self.get(section, option, default, acquire_lock=False)
            lv = v.lower()
            if lv not in self._boolean_states:
                raise ValueError("Not a boolean: %s" % (v))
            return self._boolean_states[lv]
        if acquire_lock:
            with self.lock:
                return blah()
        else:
            return blah()

    def getpath(self, section, option, default=None, acquire_lock=True):
        def blah():
            return self._get(section, resolve_path, option, default,
                             acquire_lock=False)
        if acquire_lock:
            with self.lock:
                return blah()
        else:
            return blah()

    def has_option(self, section, option, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                return RCP.has_option(self, section, option)
        else:
            return RCP.has_option(self, section, option)

    def set(self, section, option, value, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                RCP.set(self, section, option, value)
        else:
            RCP.set(self, section, option, value)

    def write(self, fp, acquire_lock=True):
        def blah():
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
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def remove_option(self, section, option, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                return RCP.remove_option(self, section, option)
        else:
            return RCP.remove_option(self, section, option)

    def remove_section(self, section, acquire_lock=True):
        def blah():
            if RCP.remove_section(self, section):
                self._section_list.remove(section)
                return True
            return False
        if acquire_lock:
            with self.lock:
                return blah()
        else:
            return blah()

    def clear(self, acquire_lock=True):
        """Removes all sections, including the DEFAULT section.
        
        acquire_lock: a boolean that, if True, will acquire this BCP's
                      lock before clearing data.  True by default.

        """
        def blah():
            sections = self.sections(acquire_lock=False) + [DEFAULTSECT]
            for s in sections:
                self.remove_section(s, acquire_lock=False)
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def load(self, acquire_lock=True):
        """Loads the data from the configuration file.
        
        acquire_lock: a boolean that, if True, will acquire this BCP's
                      lock before loading data.  True by default.

        """
        if self.dummy:
            raise Exception("Can't load() a dummy configparser")
        if acquire_lock:
            with self.lock:
                self._read(open(self.filename), self.filename)
        else:
            self._read(open(self.filename), self.filename)

    def loadfp(self, fobj, acquire_lock=True):
        """Loads configuration data from a file object.
        
        fobj:         a file object containing configuration data
        acquire_lock: a boolean that, if True, will acquire this BCP's
                      lock before loading data.  True by default.

        This BCP's filename will also be set to the resolved value of
        the file object's .name attribute, so the passed file object
        must have a .name attribute.
        
        """
        def blah():
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
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def reload(self, acquire_lock=True):
        """Reloads configuration data from the configuration file."""
        def blah():
            self.clear(acquire_lock=False)
            self.load(acquire_lock=False)
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def reloadfp(self, fobj, acquire_lock=True):
        """Reloads configuration data from a file object.

        fobj: a file object containing configuration data

        This BCP's filename will also be set to the resolved value of
        the file object's .name attribute, so the passed file object
        must have a .name attribute.
        
        """
        def blah():
            self.clear(acquire_lock=False)
            self.loadfp(fobj, acquire_lock=False)
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def save(self, acquire_lock=True):
        """Writes configuration data to the configuration file."""
        def blah():
            fobj = open(self.filename, 'w')
            try:
                self.write(fobj, acquire_lock=False)
                fobj.flush()
            finally:
                fobj.close()
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def get_if_valid(self, section, option, acquire_lock=True):
        def blah():
            try:
                val = self.get(section, option, acquire_lock=False)
                if not val:
                    return None
            except NoOptionError:
                return None
        if acquire_lock:
            with self.lock:
                return blah()
        else:
            return blah()

    def get_if_true(self, section, option, acquire_lock=True):
        def blah():
            try:
                return self.getboolean(section, option, acquire_lock=False)
            except NoOptionError:
                return None
        if acquire_lock:
            with self.lock:
                return blah()
        else:
            return blah()

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

    def get_raw(self, section, option, default=None, acquire_lock=True):
        return RawZDSConfigParser.get(self, section, option, default,
                                      acquire_lock)

    def get(self, section, option, default=None, raw=False, vars=None,
                                                            acquire_lock=True):
        def blah(rawval, option):
            ###
            # Get the option value to be interpolated.
            ###
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
        if acquire_lock:
            with self.lock:
                rawval = self.get_raw(section, option, default,
                                      acquire_lock=False)
                return blah(rawval, option)
        else:
            rawval = self.get_raw(section, option, default, acquire_lock=False)
            return blah(rawval, option)

    def items(self, section, raw=False, vars=None, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                return SCP.items(self, section, raw, vars)
        else:
            return SCP.items(self, section, raw, vars)

    def set(self, section, option, value, acquire_lock=True):
        if acquire_lock:
            with self.lock:
                return SCP.set(self, section, option, value)
        else:
            return SCP.set(self, section, option, value)

