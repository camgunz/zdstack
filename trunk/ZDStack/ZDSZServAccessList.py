from threading import Lock

from ZDStack import get_zdslog
from ZDStack.Utils import requires_instance_lock
from ZDStack.ZDSAccessList import WhiteListedAddress, Ban, IPAddress

zdslog = get_zdslog()

class NoAppropriateListError(Exception): pass

class ZServAccessList(object):

    """ZServAccessList represents a ZServ's access list.

    If a single IP ban conflicts with a whitelisted address, an
    exception is raised.  If a ban using wildcards conflicts with
    one or more whitelisted addresses, the ban is sliced into pieces,
    omitting the conflicting whitelisted addresses.

    """

    def __init__(self, zserv):
        """Initializes a ZServAccessList.

        :param zserv: the owning :class:`~ZDStack.ZServ.ZServ` instance
        :type zserv: :class:`~ZDStack.ZServ.ZServ`

        """
        self.zserv = zserv
        if not self.zserv.name in self.zserv.zdstack.banlist.sections():
            self.zserv.zdstack.banlist.add_section(self.zserv.name)
        if not self.zserv.name in self.zserv.zdstack.whitelist.sections():
            self.zserv.zdstack.whitelist.add_section(self.zserv.name)
        self.lock = Lock()

    def _discern_list(self, access_control):
        t = type(access_control)
        if t == WhiteListedAddress:
            return self.zserv.zdstack.whitelist
        elif t == Ban:
            return self.zserv.zdstack.banlist
        else:
            raise NoAppropriateListError()

    @requires_instance_lock()
    def add(self, access_control):
        """Adds an access control.

        :param access_control: a ban or whitelist to add
        :type access_control: either
                     :class:`~ZDStack.ZDSAccessList.Ban` or
                     :class:`~ZDStack.ZDSAccessList.WhiteListedAddress`

        """
        try:
            access_list = self._discern_list(access_control)
        except NoAppropriateListError:
            raise TypeError("Cannot add access control of type %s" % (t))
        access_list.add(self.zserv, access_control)
        self.zserv.check_bans()

    @requires_instance_lock()
    def remove(self, access_control):
        """Removes an access control.

        :param access_control: a ban or whitelist to add
        :type access_control: either
                     :class:`~ZDStack.ZDSAccessList.Ban` or
                     :class:`~ZDStack.ZDSAccessList.WhiteListedAddress`

        """
        try:
            access_list = self._discern_list(access_control)
        except NoAppropriateListError:
            raise TypeError("Cannot remove access control of type %s" % (t))
        access_list.remove(self.zserv, access_control)

    @requires_instance_lock()
    def search_bans(self, address):
        """Searches this ZServ's ban list for the address.

        :param address: an address to test
        :type address: string
        :returns: whether or not the address is banned.
        :rtype: boolean, string, or None

        Even if an address is present on the ban list, if it is also
        on the white list, False is returned.  If it is not on the
        white list, the reason for the ban is returned as a string.
        If the address is not found at all, None is returned.

        """
        ip_address = IPAddress(address)
        if ip_address.is_range:
            raise TypeError("Cannot test whether or not an IP range is banned")
        if self.zserv.use_global_whitelist:
            zdslog.debug("Searching global whitelist")
            if self.zserv.zdstack.whitelist.search(self.zserv, address):
                return False
        else:
            zdslog.debug("Searching global whitelist")
            x = \
                self.zserv.zdstack.whitelist.search_excluding_global(self.zserv,
                                                                     address)
            if x:
                return False
        if self.zserv.use_global_banlist:
            zdslog.debug("Searching global banlist")
            reason = self.zserv.zdstack.banlist.search(self.zserv, address)
            if reason:
                return reason
        else:
            zdslog.debug("Excluding global banlist")
            reason = \
                self.zserv.zdstack.banlist.search_excluding_global(self.zserv,
                                                                   address)
            if reason:
                return reason
        if not self.zserv.advertise and self.zserv.copy_zdaemon_banlist:
            zdslog.debug("Searching ZDaemon master banlist")
            reason = self.zserv.zdstack.zdaemon_banlist.search_global(address)
            if reason:
                return reason
        else:
            zdslog.debug("Excluding ZDaemon master banlist")
        return None

