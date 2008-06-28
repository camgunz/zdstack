import os.path

from ConfigParser import ConfigParser as CP
from ConfigParser import RawConfigParser as RCP

from ConfigParser import DEFAULTSECT, InterpolationMissingOptionError

from ZDStack.Utils import resolve_file

class BaseConfigParser:

    """BaseConfigParser is ConfigParser with reasonable file handling.

    This class is used as a MixIn class with ConfigParser and
    RawConfigParser.
    
    TODO: make threadsafe
    
    """

    def __init__(self, filename=None, allow_duplicate_sections=True):
        """Initializes a BaseConfigParser.

        filename:                 a string representing the name of a
                                  a file to parse initially
        allow_duplicate_sections: a boolean, whether or not to allow
                                  sections with duplicate names or not

        All arguments are optional.

        """
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

    def defaults(self):
        """Returns a dict of options & values in the DEFAULT section."""
        out = {}
        for x in self._defaults:
            try:
                out[self.optionxform(x)] = self.get(DEFAULTSECT, x)
            except InterpolationMissingOptionError:
                out[self.optionxform(x)] = self._defaults[x] # raw
        return out

    def set_file(self, filename):
        """Sets the location of the configuration file.

        filename: a string representing the new location of the
                  configuration file

        """
        f = resolve_file(filename)
        if not os.path.isfile(f):
            raise ValueError("Config File [%s] not found" % (filename))
        self.filename = f

    def clear(self):
        """Removes all sections, including the DEFAULT section."""
        sections = self.sections() + ['DEFAULT']
        for s in sections:
            self.remove_section(s)

    def load(self):
        """Loads the data from the configuration file."""
        self.read(self.filename)

    def loadfp(self, fobj):
        """Loads configuration data from a file object.
        
        fobj: a file object containing configuration data
        
        """
        self.readfp(fobj)

    def reload(self):
        """Reloads configuration data from the configuration file."""
        self.clear()
        self.load()

    def save(self):
        """Writes configuration data to the configuration file."""
        fobj = open(self.filename, 'w')
        try:
            self.write(fobj)
            fobj.flush()
        finally:
            fobj.close()

class RawZDSConfigParser(BaseConfigParser, RCP):

    """RawZDSConfigParser combines BaseConfigParser and RawConfigParser."""

    def __init__(self, filename=None, allow_duplicate_sections=True):
        RCP.__init__(self)
        BaseConfigParser.__init__(self, filename, allow_duplicate_sections)

class ZDSConfigParser(BaseConfigParser, CP):

    """ZDSConfigParser combines BaseConfigParser and ConfigParser."""

    def __init__(self, filename=None, allow_duplicate_sections=True):
        CP.__init__(self)
        BaseConfigParser.__init__(self, filename, allow_duplicate_sections)

