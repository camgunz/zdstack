from threading import Lock

from ZDStack.Utils import requires_instance_lock
from ZDStack.ZDSAccessList import WhiteListedAddress, Ban, AccessList, \
                                  BanList, AddressError

###
# We should actually just totally replace zserv's ban-handling mechanism.
# ZDSEventHandler should check a ZServ's access_list whenever a player
# connects, and if that player is banned and not whitelisted, immediately kick
# that player.  No mucking about with addban/killban and zd_bans.txt.
###

class WhiteListExistsError(AddressError):
    def __init__(self, whitelist):
        msg = 'WhiteList %s already exists' % (whitelist)
        AddressError.__init__(self, msg)

class BanExistsError(AddressError):
    def __init__(self, ban):
        msg = 'Ban %s already exists' % (ban)
        AddressError.__init__(self, msg)

class WhiteListNotFoundError(AddressError):
    def __init__(self, whitelist):
        msg = 'WhiteList %s not found' % (whitelist)
        AddressError.__init__(self, msg)

class BanNotFoundError(AddressError):
    def __init__(self, ban):
        msg = 'Ban %s not found' % (ban)
        AddressError.__init__(self, msg)

class ZServAccessList(object):

    """ZServAccessList represents a ZServ's access list.

    If a single IP ban conflicts with a whitelisted address, an
    exception is raised.  If a ban using wildcards conflicts with
    one or more whitelisted addresses, the ban is sliced into pieces,
    omitting the conflicting whitelisted addresses.

    """

    def __init__(self, zserv, whitelist=None, banlist=None,
                       whitelist_filename=None, banlist_filename=None):
        """Initializes a ZServAccessList.

        :param zserv: the owning :class:`~ZDStack.ZServ.ZServ` instance
        :type zserv: :class:`~ZDStack.ZServ.ZServ`
        :param whitelist: the initial list of whitelistsed addresses
        :type whitelist:
          sequence of
          :class:`~ZDStack.ZDSAccessList.WhiteListedAddress` instances
        :param banlist: the initial list of bans
        :type banlist: sequence of :class:`~ZDStack.ZDSAccessList.Ban`
                       instances
        :param whitelist_filename: the whitelist filename
        :type whitelist_filename: string
        :param banlist_filename: the banlist filename
        :type banlist_filename: string

        """
        self.whitelist = AccessList(addresses=whitelist,
                                    filename=whitelist_filename)
        self.banlist = BanList(addresses=banlist, filename=banlist_filename)
        self.zserv = zserv
        self.lock = Lock()

    @requires_instance_lock()
    def add(self, access_control):
        """Adds an access control.

        :param access_control: a ban or whitelist to add
        :type access_control:
          either :class:`~ZDStack.ZDSAccessList.Ban` or
                 :class:`~ZDStack.ZDSAccessList.WhiteListedAddress`

        """
        t = type(access_control)
        if t == WhiteListedAddress:
            self.whitelist.add(access_control)
            self.whitelist.save()
        elif t == Ban:
            for address in self.whitelist:
                if ban == address or ban in address:
                    raise WhiteListExistsError(address)
            self.banlist.add(access_control)
            self.banlist.save()
            ###
            # TODO: This should also check if any players with this IP address
            #       are currently connected to the ZServ, and kick them if so.
            ###
        else:
            raise TypeError("Cannot add access control of type %s" % (t))

    @requires_instance_lock()
    def delete(self, access_control):
        t = type(access_control)
        if t == WhiteListedAddress:
            self.whitelist.delete(access_control)
            self.whitelist.save()
        elif t == Ban:
            self.banlist.delete(access_control)
            self.banlist.save()
        else:
            raise TypeError("Cannot delete access control of type %s" % (t))

