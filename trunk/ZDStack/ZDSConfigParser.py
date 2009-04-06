from __future__ import with_statement

import os.path
import logging

from threading import Lock

from ConfigParser import RawConfigParser as RCP
from ConfigParser import SafeConfigParser as CP
from ConfigParser import DEFAULTSECT, InterpolationMissingOptionError

from ZDStack.Utils import resolve_path

###
# I could probably use super() here and not copy & paste all this code, but
# goddamn if I can figure out how it works, or if it even will work in this
# situation.
###

class RawZDSConfigParser(RCP):

    """BaseConfigParser is ConfigParser with reasonable file handling.

    This class is used as a MixIn class with ThreadsafeRawConfigParser
    and ThreadsafeConfigParser.

    """

    def __init__(self, filename=None, allow_duplicate_sections=True):
        """Initializes a BaseConfigParser.

        filename:                 a string representing the name of a
                                  a file to parse initially
        allow_duplicate_sections: a boolean, whether or not to allow
                                  sections with duplicate names or not

        All arguments are optional.

        """
        RCP.__init__(self)
        self.lock = Lock()
        if filename:
            if isinstance(filename, str):
                self.set_file(filename)
                self.load()
            elif hasattr(filename, 'readline'):
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

    def clear(self, acquire_lock=True):
        """Removes all sections, including the DEFAULT section.
        
        acquire_lock: a boolean that, if True, will acquire this BCP's
                      lock before clearing data.  True by default.

        """
        def blah():
            sections = self.sections() + ['DEFAULT']
            for s in sections:
                self.remove_section(s)
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
        if acquire_lock:
            with self.lock:
                self.read(self.filename)
        else:
            self.read(self.filename)

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
            if not hasattr(fobj, 'name'):
                es = "File objects passed to loadfp must have a .name attribute"
                raise ValueError(es)
            set_file(fobj.name, acquire_lock=False)
            self.readfp(fobj)
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def reload(self):
        """Reloads configuration data from the configuration file."""
        with self.lock:
            self.clear(acquire_lock=False)
            self.load(acquire_lock=False)

    def reloadfp(self, fobj):
        """Reloads configuration data from a file object.

        fobj: a file object containing configuration data

        This BCP's filename will also be set to the resolved value of
        the file object's .name attribute, so the passed file object
        must have a .name attribute.
        
        """
        with self.lock:
            self.clear(acquire_lock=False)
            self.loadfp(fobj)

    def save(self):
        """Writes configuration data to the configuration file."""
        with self.lock:
            fobj = open(self.filename, 'w')
            try:
                self.write(fobj)
                fobj.flush()
            finally:
                fobj.close()

    def defaults(self):
        """Returns a dict of options & values in the DEFAULT section."""
        with self.lock:
            out = dict()
            for x in self._defaults:
                try:
                    y = self.get(DEFAULTSECT, x, acquire_lock=False)
                    out[self.optionxform(x)] = y
                except InterpolationMissingOptionError:
                    out[self.optionxform(x)] = self._defaults[x] # raw
            return out

    def add_section(self, section):
        with self.lock:
            RCP.add_section(self, section)

    def remove_section(self, section):
        with self.lock:
            RCP.remove_section(self, section)

    def set(self, section, option, value):
        with self.lock:
            RCP.set(self, section, option, value)

    def remove_option(self, section, option):
        with self.lock:
            RCP.remove_option(self, section, option)

    def get(self, section, option, acquire_lock=True):
        def blah():
            return RCP.get(self, section, option)
        if acquire_lock:
            with self.lock:
                return RCP.get(self, section, option)
        else:
            return RCP.get(self, section, option)

class ZDSConfigParser(CP):

    """BaseConfigParser is ConfigParser with reasonable file handling.

    This class is used as a MixIn class with ThreadsafeRawConfigParser
    and ThreadsafeConfigParser.

    """

    def __init__(self, filename=None, allow_duplicate_sections=True):
        """Initializes a BaseConfigParser.

        filename:                 a string representing the name of a
                                  a file to parse initially
        allow_duplicate_sections: a boolean, whether or not to allow
                                  sections with duplicate names or not

        All arguments are optional.

        """
        CP.__init__(self)
        self.lock = Lock()
        if filename:
            if isinstance(filename, str):
                self.set_file(filename)
                self.load()
            elif hasattr(filename, 'readline'):
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
            f = resolve_path(filename)
            if not os.path.isfile(f):
                raise ValueError("Config File [%s] not found" % (filename))
            self.filename = f
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def clear(self, acquire_lock=True):
        """Removes all sections, including the DEFAULT section.
        
        acquire_lock: a boolean that, if True, will acquire this BCP's
                      lock before clearing data.  True by default.

        """
        def blah():
            sections = self.sections() + ['DEFAULT']
            for s in sections:
                self.remove_section(s)
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
        if acquire_lock:
            with self.lock:
                self.read(self.filename)
        else:
            self.read(self.filename)

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
            if not hasattr(fobj, 'name'):
                es = "File objects passed to loadfp must have a .name attribute"
                raise ValueError(es)
            set_file(fobj.name, acquire_lock=False)
            self.readfp(fobj)
        if acquire_lock:
            with self.lock:
                blah()
        else:
            blah()

    def reload(self):
        """Reloads configuration data from the configuration file."""
        with self.lock:
            self.clear(acquire_lock=False)
            self.load(acquire_lock=False)

    def reloadfp(self, fobj):
        """Reloads configuration data from a file object.

        fobj: a file object containing configuration data

        This BCP's filename will also be set to the resolved value of
        the file object's .name attribute, so the passed file object
        must have a .name attribute.
        
        """
        with self.lock:
            self.clear(acquire_lock=False)
            self.loadfp(fobj)

    def save(self):
        """Writes configuration data to the configuration file."""
        with self.lock:
            fobj = open(self.filename, 'w')
            try:
                self.write(fobj)
                fobj.flush()
            finally:
                fobj.close()

    def defaults(self):
        """Returns a dict of options & values in the DEFAULT section."""
        with self.lock:
            out = dict()
            for x in self._defaults:
                try:
                    y = self.get(DEFAULTSECT, x, acquire_lock=False)
                    out[self.optionxform(x)] = y
                except InterpolationMissingOptionError:
                    out[self.optionxform(x)] = self._defaults[x] # raw
        return out

    def add_section(self, section):
        with self.lock:
            CP.add_section(self, section)

    def remove_section(self, section):
        with self.lock:
            CP.remove_section(self, section)

    def set(self, section, option, value):
        with self.lock:
            CP.set(self, section, option, value)

    def remove_option(self, section, option):
        with self.lock:
            CP.remove_option(self, section, option)

    def get(self, section, option, raw=False, vars=None, acquire_lock=True):
        def blah():
            return CP.get(self, section, option, raw, vars)
        if acquire_lock:
            with self.lock:
                return CP.get(self, section, option, raw, vars)
        else:
            return CP.get(self, section, option, raw, vars)

