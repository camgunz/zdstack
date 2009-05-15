from threading import Lock

from ZDStack.Utils import requires_instance_lock

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
        ###
        # TODO: This should also check if any players with this IP address are
        #       currently connected to the ZServ, and kick them if so.
        ###

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
        if zserv.use_global_whitelist:
            if self.zserv.zdstack.whitelist.search(address):
                return False
        elif self.zserv.zdstack.whitelist.search_excluding_global(address):
            return False
        if zserv.use_global_banlist:
            reason = self.zserv.zdstack.banlist.search(address)
            if reason:
                return reason
        else:
            reason = self.zserv.zdstack.banlist.search_excluding_global(address)
            if reason:
                return reason
        if not self.zserv.advertise and self.zserv.copy_zdaemon_banlist:
            reason = self.zserv.zdstack.zdaemon_banlist.search_global(address)
            if reason:
                return reason
        return None

