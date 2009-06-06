from __future__ import with_statement

import os.path

from ConfigParser import NoSectionError, NoOptionError

from ZDStack import get_zdslog, get_zdaemon_banlist_file, get_configparser
from ZDStack.Utils import requires_instance_lock
from ZDStack.ZDSConfigParser import RawZDSConfigParser

zdslog = get_zdslog()

class AddressError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class MalformedIPAddressError(AddressError):
    def __init__(self, address):
        msg = 'Malformed IP address: [%s]' % (address)
        AddressError.__init__(self, msg)

class IPAddress(object):

    """IPAddress represents an IP address or IP addresses.

    IPAddress supports 2 types of range expansions:

      * 192.168.2.\*:     Matches anything for '*'
      * 192.168.2.17-34: Matches address from 17-34 inclusive

    IPAddresses representing IP ranges can also be tested for
    membership, for example:

    >>> IPAddress('192.168.2.4') in IPAddress('192.168.2.3-5')
    True

    """

    ###
    # There's a new 'ipaddr' module in Python 3.1 that was originally
    # written by Google (project is at
    # http://code.google.com/p/ipaddr-py/) but it doesn't do range
    # expansion exactly how we want - and would be another (albeit very
    # small) dependency anyway.
    ###

    MAX = (256 << 24) - 1 # mwahaha
    MIN = 0

    def __init__(self, address_string):
        if isinstance(address_string, int) or isinstance(address_string, long):
            tokens = list()
            for x in range(4):
                tokens.append(str(address_string & 0xFF))
                n >>= 8
            self.__tokens = [x for x in reversed(tokens)]
            self.__ranges = [[x] for x in self.tokens]
        else:
            if not address_string.count('.') == 3:
                raise MalformedIPAddressError(address_string)
            self.__tokens = list()
            self.__ranges = list()
            for x in address_string.split('.'):
                if x.isdigit():
                    x = int(x)
                    if x < 0 or x > 255:
                        raise MalformedIPAddressError(address_string)
                    self.__ranges.append([x])
                elif x == '*':
                    self.__ranges.append(range(0, 256))
                elif '-' in x:
                    min, max = x.split('-')
                    if not min.isdigit() or not max.isdigit():
                        raise MalformedIPAddressError(address_string)
                    self.__ranges.append(range(int(min), int(max) + 1))
                else:
                    raise MalformedIPAddressError(address_string)
                self.__tokens.append(x)
        self.is_range = False
        for x in self.__ranges:
            if len(x) > 1:
                self.is_range = True
                break

    def __str__(self):
        return '.'.join([str(x) for x in self.__tokens])

    def __int__(self):
        if self.is_range:
            raise TypeError("Cannot represent an IP range numerically")
        out = 0
        for x in self.__tokens:
            out = (out << 8) | x
        return out

    def __long__(self):
        return long(int(self))

    def __repr__(self):
        return u'IPAddress(%r)' % (self.__str__())

    def __iter__(self):
        """Creates a list from this IPAddress.

        :param numeric: whether to return numeric or string
                        representations of IP addresses
        :type numeric: boolean
        :rtype: list of ints/longs
        :returns: a list representation of this IPAddress.

        IPAddresses can represent multiple actual IP addresses, i.e.
        205.171.3.64-66 or 205.171.3.*.  This method returns each IP
        address this IPAddress contains as a list of strings.  If this
        IPAddress is not a range, a list with a single element is
        returned.

        """
        if not self.is_range:
            return [int(self)]
        out = list()
        for a in self.ranges[0]:
            for b in self.ranges[1]:
                for c in self.ranges[2]:
                    for d in self.ranges[3]:
                        address = 0
                        for x in (a, b, c, d):
                            address = (address << 8) | x
                        out.append(address)
        return out.__iter__()

    def __contains__(self, ip_address):
        """Tests whether this IP address matches the given address.

        :param ip_address: the :class:`~ZDStack.ZDSAccessList.IPAddress`
                           to test
        :type ip_address: :class:`~ZDStack.ZDSAccessList.IPAddress` or
                          string
        :rtype: boolean

        """
        if not self.is_range:
            es = "Non-range IPAddresses cannot contain other IPAddresses"
            raise TypeError(es)
        if not isinstance(ip_address, IPAddress):
            try:
                ip_address = self.from_address(ip_address)
            except (MalformedIPAddressError, ValueError, TypeError):
                return False
        if not ip_address.is_range:
            n = int(ip_address)
            return n >= self.min and n <= self.max
        else:
            return ip_address.min > self.min and ip_address.max < self.max

    def __eq__(self, ip_address):
        """Tests whether this IP address matches the given address.

        :param ip_address: the :class:`~ZDStack.ZDSAccessList.IPAddress`
                           to test
        :type ip_address: :class:`~ZDStack.ZDSAccessList.IPAddress` or
                          string
        :rtype: boolean

        """
        if not isinstance(ip_address, IPAddress):
            try:
                ip_address = self.from_address(ip_address)
            except (MalformedIPAddressError, ValueError, TypeError):
                return False
        if not self.is_range == ip_address.is_range:
            return False
        if self.is_range:
            return self.min == ip_address.min and self.max == ip_address.max
        else:
            return int(self) == int(ip_address)

    def __lt__(self, ip_address):
        return int(self) < int(ip_address)

    def __gt__(self, ip_address):
        return int(self) > int(ip_address)

    def __ne__(self, ip_address):
        return not self.__eq__(ip_address)

    def __add__(self, x):
        if self.is_range:
            raise TypeError("Can't increment an IPAddress using wildcards")
        return self.from_address(int(self) + int(x))

    def __sub__(self, x):
        if self.is_range:
            raise TypeError("Can't increment an IPAddress using wildcards")
        return self.from_address(int(self) - int(x))

    @property
    def min(self):
        """The lowest int/long this IPAddress represents."""
        out = 0
        for x in self.__ranges:
            out = (out << 8) | x[0]
        return out

    @property
    def max(self):
        """The highest int/long this IPAddress represents."""
        out = 0
        for x in self.__ranges:
            out = (out << 8) | x[-1]
        return out

    def from_address(self, address):
        """Creates an object of the same type as this instance.

        :param address: an IP address
        :type address: either string or int/long
        :returns: An object of the same type as this instance, with a
                  separate address.  This is most useful for
                  subclasses.

        """
        return type(self)(address)

    def render(self):
        """Renders this IPAddress.

        :rtype: string
        :returns: a nicely formatted string representing this
                  IPAddress, suitable for re-parsing or saving to a
                  file

        """
        if not self.is_range:
            return str(self)
        return '\n'.join([str(self.from_address(x)) for x in self])

class Ban(IPAddress):

    ###
    # It would be neat if we could add names to this somehow, but the ZDaemon
    # banlist file format is no help, example:
    #
    # 69.183.41.*#wazzup
    # 69.88.42.*#cheating
    #
    # 1st line is a name, second line is a reason, and without a magic list
    # of "reasons" (which will never be 100% anyway), we can't do anything
    # about this.  So meh.
    ###

    def __init__(self, address_string, reason=None):
        IPAddress.__init__(self, address_string)
        self.reason = reason

    def __repr__(self):
        return 'Ban(%r, %r)' % (IPAddress.__str__(self), self.reason)

    def render(self):
        """Renders this Ban.

        :rtype: string
        :returns: a string representation of the ban in ZDaemon banlist
                  format.  Unless saving into a zserv's banlist file,
                  you probably just want to use the str() method on Ban
                  instances instead.
        """
        default = IPAddress.to_list(self)
        if self.reason:
            extra_stuff = '#' + self.reason
            default = [x + extra_stuff for x in default]
        return '\n'.join(default)

class WhiteListedAddress(IPAddress):

    def __init__(self, address_string, reason=None):
        ###
        # The initializer takes 2 arguments because configparser options come
        # in option: value pairs, and this corresponds to
        # address_string: reason in our case... even though whitelisted are
        # all obviously whitelisted for the same reason.  Thus a
        # WhiteListedAddress takes a reason argument, but it is always set to
        # None.
        ###
        IPAddress.__init__(self, address_string)
        self.reason = None

    def __repr__(self):
        return 'WhiteListedAddress(%r)' % (IPAddress.__str__(self))

class AddressList(RawZDSConfigParser):

    def __init__(self, item_class, filename=None, dummy=False):
        self.item_class = item_class
        RawZDSConfigParser.__init__(self, filename, dummy)

    @requires_instance_lock()
    def add_global(self, address, reason=None):
        """Adds an address to the global list.

        :param address: an address to add to the list
        :type address: string
        :param reason: reason for adding the address (optional)
        :type reason: string

        """
        reason = reason or ''
        RawZDSConfigParser.set(self, 'DEFAULT', address, reason,
                               acquire_lock=False)
        RawZDSConfigParser.save(self, acquire_lock=False)

    @requires_instance_lock()
    def remove_global(self, address):
        """Removes an address from the global list.

        :param address: an address to remove from the list
        :type address: string
        :returns: whether or not the address existed
        :rtype: boolean

        """
        out = RawZDSConfigParser.remove_option(self, 'DEFAULT', address,
                                               acquire_lock=False)
        RawZDSConfigParser.save(self, acquire_lock=False)
        return out

    @requires_instance_lock()
    def add(self, zserv, address, reason=None):
        """Adds an address to a ZServ's list.

        :param zserv: a :class:`~ZDStack.ZServ.ZServ` to add the
                      address to
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :param address: an address to add to the list
        :type address: string
        :param reason: reason for adding the address (optional)
        :type reason: string

        """
        reason = reason or ''
        RawZDSConfigParser.set(self, zserv.name, address, reason,
                               acquire_lock=False)
        RawZDSConfigParser.save(self, acquire_lock=False)

    @requires_instance_lock()
    def remove(self, zserv, address):
        """Removes an address from a ZServ's list.

        :param zserv: a :class:`~ZDStack.ZServ.ZServ` to remove the
                      address from
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :param address: an address to remove from the list
        :type address: string
        :returns: whether or not the address existed
        :rtype: boolean

        """
        out = RawZDSConfigParser.remove_option(self, zserv.name, address,
                                               acquire_lock=False)
        RawZDSConfigParser.save(self, acquire_lock=False)
        return out

    @requires_instance_lock()
    def get_all_global(self):
        """Gets all global addresses.

        :rtype: a sequence of addresses

        """
        return [self.item_class(*x) for x in self._defaults.items()]

    @requires_instance_lock()
    def get_all(self, zserv):
        """Gets all addresses from a ZServ's list.

        :param zserv: a :class:`~ZDStack.ZServ.ZServ` from which to get
                      the addresses
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :rtype: a sequence of addresses

        """
        items = self.items(zserv.name, acquire_lock=False)
        return [self.item_class(*x) for x in items]

    @requires_instance_lock()
    def get_all_excluding_global(self, zserv):
        """Gets all addresses from a ZServ's list, excluding globals.

        :param zserv: a :class:`~ZDStack.ZServ.ZServ` from which to get
                      the addresses
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :rtype: a sequence of addresses

        """
        if not self.has_section(zserv.name, acquire_lock=False):
            raise NoSectionError(zserv.name)
        out = [self.item_class(*x) for x in self._sections(zserv.name).items()]
        return out

    @requires_instance_lock()
    def get_global(self, address):
        """Gets a global address.

        :param address: an address to match up and return
        :type address: string
        :returns: a matching IP address or None if not found
        :rtype: :class:`~ZDStack.ZDSAccessList.IPAddress`

        """
        v = RawZDSConfigParser.get(self, 'DEFAULT', address, default=False,
                                         acquire_lock=False)
        return v and self.item_class(address, v) or False

    @requires_instance_lock()
    def get(self, zserv, address):
        """Gets an address from a ZServ's list.

        :param zserv: a :class:`~ZDStack.ZServ.ZServ` from which to get
                      the address
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :param address: an address to remove from the list
        :type address: string
        :returns: a matching IP address; searches both the ZServ's
                  address list and the global address list; if no
                  matching addresses are found, returns None
        :rtype: :class:`~ZDStack.ZDSAccessList.IPAddress` or None

        """
        v = RawZDSConfigParser.get(self, zserv.name, address, default=False,
                                         acquire_lock=False)
        return v and self.item_class(address, v) or False

    @requires_instance_lock()
    def get_excluding_global(self, zserv, address):
        """Gets an address from a ZServ's list.

        :param zserv: a :class:`~ZDStack.ZServ.ZServ` from which to get
                      the address
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :param address: an address to remove from the list
        :type address: string
        :returns: a matching IP address; searches only the ZServ's
                  address list
        :rtype: :class:`~ZDStack.ZDSAccessList.IPAddress`

        """
        v = RawZDSConfigParser.get_excluding_defaults(self, zserv.name,
                                                            address,
                                                            default=False,
                                                            acquire_lock=False)
        return v and self.item_class(address, v) or False

    def _search(self, address, addresses):
        ip_address = self.item_class(address)
        for x in addresses:
            if ip_address == x or ip_address in x:
                return x.reason and x.reason or True
        return False

    @requires_instance_lock()
    def search_global(self, address):
        """Searches for an address.

        :param address: an address to search for
        :type address: string
        :returns: False if the address is not found, True or the reason
                  listed with the address if found.
        :rtype: boolean or string

        This method will search for IP addresses in the global address
        list that either match or contain the given address, using the
        wildcard expansions supported by
        :class:`~ZDStack.ZDSAccessList.IPAddress`.

        """
        addresses = [self.item_class(*x) for x in self._defaults.items()]
        return self._search(address, self.get_all_global(acquire_lock=False))

    @requires_instance_lock()
    def search(self, zserv, address):
        """Searches for an address.

        :param zserv: a :class:`~ZDStack.ZServ.ZServ` from which to get
                      the address
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :param address: an address to search for
        :type address: string
        :returns: False if the address is not found, True or the reason
                  listed with the address if found.
        :rtype: boolean or string

        This method will search for IP addresses in a ZServ's address
        list that either match or contain the given address, using the
        wildcard expansions supported by
        :class:`~ZDStack.ZDSAccessList.IPAddress`.

        """
        return self._search(address, self.get_all(zserv, acquire_lock=False))

    @requires_instance_lock()
    def search_excluding_global(self, zserv, address):
        """Searches for an address.

        :param zserv: a :class:`~ZDStack.ZServ.ZServ` from which to get
                      the address
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :param address: an address to search for
        :type address: string
        :returns: False if the address is not found, True or the reason
                  listed with the address if found.
        :rtype: boolean or string

        This method will search for IP addresses in a ZServ's address
        list that either match or contain the given address, using the
        wildcard expansions supported by
        :class:`~ZDStack.ZDSAccessList.IPAddress`.  This method does
        not consider matching addresses found only in the global list
        as matches.

        """
        addresses = self.get_all_excluding_global(zserv, acquire_lock=False)
        return self._search(address, addresses)

class WhiteList(AddressList):

    def __init__(self, dummy=False):
        cp = get_configparser()
        filename = cp.getpath('DEFAULT', 'zdstack_whitelist_file')
        AddressList.__init__(self, WhiteListedAddress, filename=filename,
                                   dummy=dummy)

class BanList(AddressList):

    def __init__(self, dummy=False):
        cp = get_configparser()
        filename = cp.getpath('DEFAULT', 'zdstack_banlist_file')
        AddressList.__init__(self, Ban, filename=filename, dummy=dummy)

class ZDaemonBanList(AddressList):

    def __init__(self, dummy=False):
        filename = get_zdaemon_banlist_file()
        AddressList.__init__(self, Ban, filename=filename, dummy=dummy)

