#!/usr/bin/env python

import pprint
from xmlrpclib import ServerProxy

sp = ServerProxy('http://totaltrash.org:8888')
zn = 'ZDCTF Test'
# pprint.pprint(sp.system.listMethods())
print "=== All Players ==="
pprint.pprint(sp.get_all_players(zn))
print "\n=== All Teams ==="
pprint.pprint(sp.get_all_teams(zn))
print "\n=== Current Map ==="
pprint.pprint(sp.get_current_map(zn))
print "\n=== All ZServs ==="
pprint.pprint(sp.get_all_zservs())
print "\n=== Remembered Stats ==="
pprint.pprint(sp.get_remembered_stats(zn))

