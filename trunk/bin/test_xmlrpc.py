#!/usr/bin/env python

import os
import time
import pprint
from xmlrpclib import ServerProxy

sp = ServerProxy('http://69.64.49.142:8888')
cn1 = 'Coop Test'
cn2 = 'ZDCTF Test'
dn = 'D5M1 Test'
fn = 'FFA Test'
tn = 'TeamDM Test'
nl = (cn1, cn2, dn, fn, tn)
sp.reload_config()
# sp.start_zserv(tn)
# sp.start_zserv('Coop Test')
# sp.start_zserv('TeamDM Test')
# sp.send_to_zserv(cn, "kick 0 later\n")
# pprint.pprint(sp.system.listMethods())
# for n in nl:
#     pprint.pprint(sp.get_all_players(n))
# print "=== CTF Players ==="
# pprint.pprint(sp.get_all_players(cn))
# print "=== Duel Players ==="
# pprint.pprint(sp.get_all_players(dn))
# print "\n=== All Teams ==="
# pprint.pprint(sp.get_all_teams(cn))
# print "\n=== Current Map ==="
# pprint.pprint(sp.get_current_map(cn))
# print "\n=== All ZServs ==="
# pprint.pprint(sp.get_all_zservs())
# print "\n=== Remembered Stats ==="
# pprint.pprint(sp.get_remembered_stats(cn))
# for n in (cn, dn):
#     print "Stopping [%s]: %s" % (n, sp.stop_zserv(n))
#     time.sleep(2)
#     os.system('ps auxww | grep 1100')
#     print "Starting [%s]: %s" % (n, sp.start_zserv(n))
#     time.sleep(2)
#     os.system('ps auxww | grep 1100')

