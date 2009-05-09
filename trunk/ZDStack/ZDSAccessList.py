import os.path

from ZDStack import get_zdslog
from ZDStack.Utils import create_file, resolve_path, requires_instance_lock
from ZDStack.ZDSConfigParser import RawZDSConfigParser

zdslog = get_zdslog()

class AddressError(Exception):
    def __init__(self, msg):
        Exception.__init__(msg)

class AddressExistsError(AddressError):
    def __init__(self, address):
        msg = 'Address %s already exists' % (address)
        AddressError.__init__(self, msg)

class AddressNotFoundError(AddressError):
    def __init__(self, address):
        msg = 'Address %s not found' % (address)
        AddressError.__init__(self, msg)

class MalformedIPAddressError(AddressError):
    def __init__(self, address):
        msg = 'Malformed IP address: [%s]' % (address)
        AddressError.__init__(self, msg)

class IPAddress:

    def __init__(self, address_string):
        if not address_string.count('.') == 3:
            raise MalformedIPAddressError(address_string)
        self.stars_in_ip = False
        tokens = list()
        for x in address_string.split('.'):
            if x != '*':
                if self.stars_in_ip:
                    es = "'*'s must also be applied to all lower classes"
                    raise ValueError(es)
                x = int(x)
                if n < 0 or n > 255:
                    raise MalformedIPAddressError(address_string)
            else:
                self.stars_in_ip = True
            tokens.append(x)
        self.class_a, self.class_b, self.class_c, self.class_d = tokens

    def __iter__(self):
        x = [self.class_a, self.class_b, self.class_c, self.class_d]
        return x.__iter__()

    def __str__(self):
        return '.'.join([str(x) for x in self])

    def __repr__(self):
        return u'IPAddress(%r)' % (str(self))

    def __contains__(self, ip_address):
        """Tests whether this IP address matches the given address.

        :param ip_address: the :class:`~ZDStack.ZDSAccessList.IPAddress`
                           to test
        :type ip_address: :class:`~ZDStack.ZDSAccessList.IPAddress` or
                          string
        :rtype: boolean

        This will expand '*' characters to match anything.

        """
        ###
        # I would rather this didn't also match equal IPAddresses, but meh.
        ###
        if not isinstance(ip_address, IPAddress):
            if not isinstance(ip_address, basestring):
                return False
            else:
                try:
                    ip_address = IPAddress(ip_address)
                except (MalformedIPAddressError, ValueError):
                    return False
        for x, y in zip(self, ip_address):
            if x != '*' and x != y:
                return False
        return True

    def __lt__(self, ip_address):
        for x, y in zip(self, ip_address):
            if x != '*' and x >= y:
                return False
        return True

    def __gt__(self, ip_address):
        for x, y in zip(self, ip_address):
            if x == '*' or x <= y:
                return False
        return True

    def __eq__(self, ip_address):
        """Tests whether this IP address matches the given address.

        :param ip_address: the :class:`~ZDStack.ZDSAccessList.IPAddress`
                           to test
        :type ip_address: :class:`~ZDStack.ZDSAccessList.IPAddress` or
                          string

        This does not expand '*' characters, addresses must match
        exactly, wildcards included.

        """
        if not isinstance(ip_address, IPAddress):
            if not isinstance(ip_address, basestring):
                return False
            else:
                try:
                    ip_address = IPAddress(ip_address)
                except (MalformedIPAddressError, ValueError):
                    return False
        for x, y in zip(self, ip_address):
            if x != y:
                return False
        return True

    def __ne__(self, a):
        return not self.__eq__(a)

    ###
    # I could accomplish the following by not using strings/integers...
    # but laziness....
    ###

    def increment(self):
        """Adds 1 to this IP address.

        This works across classes, so '206.205.128.255'.increment()
        produces '206.205.129.0'.  However, using this method on an
        IPAddress using wildcards raises an Exception.

        """
        if self.stars_in_ip:
            raise TypeError("Can't increment an IPAddress using wildcards")
        if self.class_d != 255:
            self.class_d += 1
        elif self.class_c != 255:
            self.class_d = 0
            self.class_c += 1
        elif self.class_b != 255:
            self.class_d = 0
            self.class_c = 0
            self.class_b += 1
        elif self.class_a != 255:
            self.class_d = 0
            self.class_c = 0
            self.class_b = 0
            self.class_a += 1
        else:
            raise TypeError("Can't increment IPAddress any further")

    def decrement(self):
        """Subtracts 1 from this IP address.

        This works across classes, so '206.205.129.0'.decrement()
        produces '206.205.128.255'.  However, using this method on an
        IPAddress using wildcards raises an Exception.

        """
        if self.stars_in_ip:
            raise TypeError("Can't increment an IPAddress using wildcards")
        if self.class_d != 0:
            self.class_d -= 1
        elif self.class_c != 0:
            self.class_d = 255
            self.class_c -= 1
        elif self.class_b != 0:
            self.class_d = 255
            self.class_c = 255
            self.class_b -= 1
        elif self.class_a != 0:
            self.class_d = 255
            self.class_c = 255
            self.class_b = 255
            self.class_a -= 1
        else:
            raise TypeError("Can't decrement IPAddress any further")

class AddressList(list):

    def __contains__(self, x):
        for y in self:
            if x == y or y in x:
                return True
        return False

class Ban(IPAddress):

    def __init__(self, address_string, names=[], reason=None):
        IPAddress.__init__(self, address_string)
        self.names = names
        self.reason = reason

    def __str__(self):
        s = IPAddress.__str__(self) + '#'
        if self.names:
            names = '/'.join(self.names).join(['<', '>'])
            s += names
        if self.reason:
            s += ': ' + self.reason
        return s

    def __repr__(self):
        return 'Ban(%s)' % (IPAddress.__str__(self))

class AccessList(RawZDSConfigParser):

    """AccessList maintains a list of banned and whitelisted addresses.

    .. attribute:: whitelist
      A :class:`~ZDStack.ZDSAccessList.AddressList containing
      :class:`~ZDStack.ZDSAccessList.IPAddress` instances

    .. attribute:: banlist
      A :class:`~ZDStack.ZDSAccessList.AddressList containing
      :class:`~ZDStack.ZDSAccessList.Ban` instances

    """

    def __init__(self, filename=None, dummy=False):
        """Initializes an AccessList.
        
        :param filename: the accesslist filename
        :type filename: string
        :param dummy: indicates that this AccessList is a dummy, and
                      therefore shouldn't perform checks on the
                      underlying file
        :type dummy: boolean

        All arguments are optional.

        """
        self.whitelist = AddressList()
        self.banlist = AddressList()
        RawZDSConfigParser.__init__(self, filename, dummy)

    @requires_instance_lock()
    def _sync_lists(self):
        for address_string in self.options('bans'):
            self.banlist.append(Ban(address_string))
        for address_string in self.options('whitelist'):
            self.whitelist.append(IPAddress(address_string))

    def _read(self, fobj, filename):
        RawZDSConfigParser._read(self, fobj, filename)
        modified = False
        if not 'bans' in self._sections:
            self.add_section('bans')
            modified = True
        if not 'whitelist' in self._sections:
            self.add_section('whitelist')
            modified = True
        self._sync_lists(acquire_lock=False)
        if modified:
            self.save(acquire_lock=False)

    @requires_instance_lock()
    def add_ban(self, address, reason=''):
        """Bans an address.

        :param address: an IP address to unban
        :type address: string
        :param reason: a reason for the ban
        :type reason: string

        """
        self.set('bans', address, reason, acquire_lock=False)
        self._sync_lists(acquire_lock=False)
        self.save(acquire_lock=False)

    @requires_instance_lock()
    def remove_ban(self, address):
        """Un-bans an address

        :param address: an IP address to un-ban
        :type address: string

        """
        self.remove_option('bans', address, acquire_lock=False)
        self._sync_lists(acquire_lock=False)
        self.save(acquire_lock=False)

    @requires_instance_lock()
    def add_whitelist(self, address):
        """Whitelists an address.

        :param address: an IP address to un-ban
        :type address: string

        """
        self.set('whitelist', address, '', acquire_lock=False)
        self._sync_lists(acquire_lock=False)
        self.save(acquire_lock=False)

    @requires_instance_lock()
    def remove_whitelist(self, address):
        """Un-whitelists an address.

        :param address: an IP address to un-ban
        :type address: string

        """
        self.remove_option('whitelist', address, acquire_lock=False)
        self._sync_lists(acquire_lock=False)
        self.save(acquire_lock=False)

    @requires_instance_lock()
    def clear_bans(self):
        """Clears all bans."""
        self.remove_section('bans', acquire_lock=False)
        self.add_section('bans', acquire_lock=False)
        self.save(acquire_lock=False)

    @requires_instance_lock()
    def clear_whitelist(self):
        """Clears whitelist."""
        self.remove_section('whitelist', acquire_lock=False)
        self.add_section('whitelist', acquire_lock=False)
        self.save(acquire_lock=False)

    @requires_instance_lock()
    def clear(self):
        """Clears whitelist and all bans."""
        self.clear_whitelist(acquire_lock=False)
        self.clear_bans(acquire_lock=False)

