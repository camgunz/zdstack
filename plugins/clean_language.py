RACIST_WORDS = ['nigger', 'kike', 'wop', 'spic', 'cracker', 'honky', 'porchmonkey', 'beaner', 'gook']

EXPLITIVES = ['fuck', 'shit', 'damn', 'ass', 'bitch', 'faggot', 'fag', 'phag']

VULGAR_WORDS = ['cock', 'cunt', 'pussy', 'dick', 'anus', 'asshole', 'vagina', 'penis']

BAD_WORDS = RACIST_WORDS + EXPLITIVES + VULGAR_WORDS

BAD_LANGUAGE_LIMIT = 2

def clean_language(event, zserv):
    if not event.type == 'message':
        return
    p = zserv.distill_player(event.data['possible_player_names'])
    if not p: # oddly, the messenger could not be distilled
        return
    for w in BAD_WORDS:
        if w in event.data['contents']:
            if not hasattr(p, 'bad_language'):
                p.bad_language = 0
            p.bad_language += 1
            if p.bad_language >= BAD_LANGUAGE_LIMIT:
                p.bad_language = 0
                zserv.zkick(p.number)
            else:
                zserv.zsay("%s, this is a clean language server.  %d more violations and you will be kicked." % (p.name, BAD_LANGUAGE_LIMIT - p.bad_language))
