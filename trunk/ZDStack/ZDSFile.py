from __future__ import with_statement

import os.path

from threading import Lock

from ZDStack.Utils import resolve_path, requires_instance_lock

class SynchronizedFile:

    """SynchronizedFile is a threadsafe interface to an on-disk file.

    .. attribute:: lock
        A Lock that must be acquired before using the SynchronizedFile

    .. attribute:: dummy
        A boolean, whether or not the SynchronizedFile is a dummy and
        therefore shouldn't perform checks on the underlying file
    
    """

    def __init__(self, filename=None, dummy=False):
        """Initializes a SynchronizedFile.

        :param filename: the name of the file to load initially
        :type filename: string
        :param dummy: indicates that this SynchronizedFile is a
                      dummy, and therefore shouldn't perform checks on
                      the underlying file.
        :type dummy: boolean

        All arguments are optional.

        """
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
        """Sets the location of the on-disk file.

        :param filename: the new location of the on-disk file
        :type filename: string

        """
        if self.dummy:
            return
        f = resolve_path(filename)
        if not os.path.isfile(f):
            raise ValueError("File [%s] not found" % (filename))
        self.filename = f

    @requires_instance_lock()
    def clear(self):
        """Here so subclasses can override."""
        raise NotImplementedError()

    @requires_instance_lock()
    def load(self):
        """Loads data from the on-disk file."""
        if self.dummy:
            raise Exception("Can't load() a dummy SynchronizedFile")
        self._read(open(self.filename), self.filename)

    @requires_instance_lock()
    def loadfp(self, fobj):
        """Loads data from a file object.
        
        :param fobj: the file containing data
        :type fobj: file

        This SynchronizedFile's filename will also be set to the
        resolved value of the file object's .name attribute, so the
        passed file object must have a .name attribute.
        
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
        """Reloads data from the on-disk file."""
        if not self.filename:
            raise Exception("Can't reload, no filename has been set")
        self.clear(acquire_lock=False)
        self.load(acquire_lock=False)

    @requires_instance_lock()
    def reloadfp(self, fobj):
        """Reloads data from a file object.
        
        :param fobj: the file containing data
        :type fobj: file

        This SynchronizedFile's filename will also be set to the
        resolved value of the file object's .name attribute, so the
        passed file object must have a .name attribute.
        
        """
        self.clear(acquire_lock=False)
        self.loadfp(fobj, acquire_lock=False)

    @requires_instance_lock()
    def save(self):
        """Writes this SynchronizedFile to disk.
        
        The data that is written is the output of str(self), so
        subclasses can override __str__.
        
        """
        fobj = open(self.filename, 'w')
        try:
            fobj.write(str(self))
            fobj.flush()
        finally:
            fobj.close()

    def _read(self, fobj, filename):
        """Reads data.

        :param fobj: a file to read from
        :type fobj: file
        :param filename: the name of the file to read from
        :type filename: string

        This is here for subclasses to override.

        """
        raise NotImplementedError()

