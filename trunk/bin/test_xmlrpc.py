#!/usr/bin/env python

import pprint
from xmlrpclib import ServerProxy

sp = ServerProxy('http://69.64.49.142:8888')
cn = 'ZDCTF Test'
dn = 'D5M1 Test'
# pprint.pprint(sp.system.listMethods())
print "=== CTF Players ==="
pprint.pprint(sp.get_all_players(cn))
print "=== Duel Players ==="
pprint.pprint(sp.get_all_players(dn))
# print "\n=== All Teams ==="
# pprint.pprint(sp.get_all_teams(zn))
# print "\n=== Current Map ==="
# pprint.pprint(sp.get_current_map(zn))
# print "\n=== All ZServs ==="
# pprint.pprint(sp.get_all_zservs())
# print "\n=== Remembered Stats ==="
# pprint.pprint(sp.get_remembered_stats(zn))

