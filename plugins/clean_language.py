RACIST_WORDS = ['nigger', 'kike', 'wop', 'spic', 'cracker', 'honky', 'porchmonkey', 'beaner', 'gook']

EXPLITIVES = ['fuck', 'shit', 'damn', 'ass', 'bitch', 'faggot', 'fag', 'phag']

VULGAR_WORDS = ['cock', 'cunt', 'pussy', 'dick', 'anus', 'asshole', 'vagina', 'penis']

BAD_WORDS = RACIST_WORDS + EXPLITIVES + VULGAR_WORDS

BAD_LANGUAGE_LIMIT = 2

def clean_language(event, zserv):
    if not event.type == 'message':
        return
    message, messenger = (event.data['message'], event.data['messenger'])
    for w in BAD_WORDS:
        if w in message:
            if not hasattr(messenger, 'bad_language'):
                messenger.bad_language = 0
            messenger.bad_language += 1
            if messenger.bad_language >= BAD_LANGUAGE_LIMIT:
                messenger.bad_language = 0
                ###
                # This should be switched to addtempban sometime soon
                zserv.zkick(messenger.number, "Bad language")
            else:
                s = "%s, this is a clean language server."
                s += "  %d more violations and you will be kicked."
                zserv.zsay(s % (messenger.name,
                                BAD_LANGUAGE_LIMIT - messenger.bad_language))
