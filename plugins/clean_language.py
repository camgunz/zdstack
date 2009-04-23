RACIST_WORDS = ['nigger', 'kike', 'wop', 'spic', 'cracker', 'honky',
                'porchmonkey', 'beaner', 'gook', 'wetback']
EXPLITIVES = ['fuck', 'shit', 'damn', 'ass', 'bitch', 'faggot', 'fag', 'phag']
VULGAR_WORDS = ['cock', 'cunt', 'pussy', 'dick', 'anus', 'asshole', 'vagina',
                'penis']
BAD_WORDS = RACIST_WORDS + EXPLITIVES + VULGAR_WORDS
BAD_LANGUAGE_LIMIT = 2
BAN_LENGTH = 15 # 15 minutes

def clean_language(event, zserv):
    if not event.type == 'message':
        return
    contents = event.data['message'].lower()
    p = event.data['messenger']
    for w in BAD_WORDS:
        if w in contents:
            if not hasattr(p, 'bad_language'):
                p.bad_language = 0
            p.bad_language += 1
            if p.bad_language >= BAD_LANGUAGE_LIMIT:
                p.bad_language = 0
                zserv.zaddtimedban(BAN_LENGTH, p.ip, reason="Language")
            else:
                zs = "%s, this is a clean language server.  %d more violations"
                zs += " and you will be temporarily banned."
                zserv.zsay(zs % (p.name, BAD_LANGUAGE_LIMIT - p.bad_language))
            break

