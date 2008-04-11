#!/usr/bin/env python

import pprint
from xmlrpclib import ServerProxy

sp = ServerProxy('http://totaltrash.org:8888')
zn = 'ZDCTF Test'
# pprint.pprint(sp.system.listMethods())
pprint.pprint(sp.get_all_players(zn))
pprint.pprint(sp.get_all_teams(zn))
pprint.pprint(sp.get_all_maps(zn))

