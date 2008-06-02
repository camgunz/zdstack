import os.path

from ConfigParser import ConfigParser as CP
from ConfigParser import RawConfigParser as RCP

from ConfigParser import DEFAULTSECT, InterpolationMissingOptionError

from ZDStack.Utils import resolve_file

class BaseConfigParser:

    def __init__(self, filename=None, allow_duplicate_sections=True):
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
        out = {}
        for x in self._defaults:
            try:
                out[self.optionxform(x)] = self.get(DEFAULTSECT, x)
            except InterpolationMissingOptionError:
                out[self.optionxform(x)] = self._defaults[x] # raw
        return out

    def set_file(self, filename):
        f = resolve_file(filename)
        if not os.path.isfile(f):
            raise ValueError("Config File [%s] not found" % (filename))
        self.filename = f

    def clear(self):
        sections = self.sections() + ['DEFAULT']
        for s in sections:
            self.remove_section(s)

    def load(self):
        self.read(self.filename)

    def loadfp(self, fobj):
        self.readfp(fobj)

    def reload(self):
        self.clear()
        self.load()

    def save(self):
        fobj = open(self.filename, 'w')
        try:
            self.write(fobj)
            fobj.flush()
        finally:
            fobj.close()

class RawZDSConfigParser(BaseConfigParser, RCP):

    def __init__(self, filename=None, allow_duplicate_sections=True):
        RCP.__init__(self)
        BaseConfigParser.__init__(self, filename, allow_duplicate_sections)

class ZDSConfigParser(BaseConfigParser, CP):

    def __init__(self, filename=None, allow_duplicate_sections=True):
        CP.__init__(self)
        BaseConfigParser.__init__(self, filename, allow_duplicate_sections)

