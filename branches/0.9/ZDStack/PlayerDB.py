from base64 import b64decode
from ZDStack import get_database, log, debug

def save_player_ip(player_name, encoded_player_name, player_ip):
    debug("[%s, %s, %s]" % (player_name, encoded_player_name, player_ip))
    return # for debugging
    db = get_database()
    if not db:
        es = "PyXSE not found, Player => IP matching unavailable"
        log(es)
        return
    rs = db.select('players',
                   where=[lambda r: r['name'] == encoded_player_name])
    rs = [x for x in rs]
    if not rs:
        db.insert('players', values=(encoded_player_name, player_ip))
    addresses = set()
    for r in rs:
        for address in r['addresses'].split(','):
            addresses.add(address)
    if player_ip not in addresses:
        def log_ip(row):
            a = row['addresses'].split(',')
            a.append(player_ip)
            s = set()
            a = [x for x in a if x not in s and not s.add(x)]
            row['addresses'] = ','.join(a)
        db.update('players', set=[log_ip],
                   where=[lambda r: r['name'] == encoded_player_name])

def get_possible_aliases(name, encoded_name, ip_addresses=[]):
    debug()
    db = get_database()
    if not db:
        log("PyXSE not found, Player => IP Logging disabled")
        return []
    def get_ip_match_func(addresses):
        # Takes a set() of strings representing IP addresses
        f = lambda x: list(addresses.intersection(x.split(',')))
        return lambda r: f(r['addresses'])
    names = set([encoded_name])
    addresses = set(ip_addresses)
    number_of_names = len(names)
    rs = db.select('players', where=[lambda r: r['name'] in names])
    for r in rs:
        for address in r['addresses'].split(','):
            addresses.add(address)
    else:
        es = "Found new player [%s], encoded: [%s], all names: [%s]"
        debug(es % (name, encoded_name,
                  ', '.join([x['name'] for x in db.select('players')])))
    number_of_addresses = len(addresses)
    if number_of_addresses:
        rs = db.select('players', where=[get_ip_match_func(addresses)])
        for r in rs:
            for address in r['addresses'].split(','):
                addresses.add(address)
            names.add(r['name'])
    while len(names) != number_of_names and \
          len(addresses) != number_of_addresses: # names/addresses were added
        number_of_names = len(names)
        number_of_addresses = len(addresses)
        rs = db.select('players', where=[lambda r: r['name'] in names])
        for r in rs:
            for address in r['addresses'].split(','):
                addresses.add(address)
        if number_of_addresses:
            rs = db.select('players', where=[get_ip_match_func(addresses)])
            for r in rs:
                for address in r['addresses'].split(','):
                    addresses.add(address)
                names.add(r['name'])
    return sorted([b64decode(x) for x in list(names)])

