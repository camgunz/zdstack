import os.path

from datetime import datetime, timedelta
from threading import Thread

def yes(x):
    return x.lower() in ('y', 'yes', 't', 'true', '1', 'on', 'absolutely')

def no(x):
    return x.lower() in ('n', 'no', 'f', 'false', '0', 'off', 'never')

def timedelta_in_seconds(x):
    return (x.days * 86400) + x.seconds

def start_thread(target, name=None, daemonic=True):
    debug("Starting thread [%s]" % (name))
    t = Thread(target=target, name=name)
    t.setDaemon(daemonic)
    t.start()
    return t

def get_logfile_suffix(roll=False):
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)
    if roll and now.hour == 23:
        today += timedelta(days=1)
    return today.strftime('-%Y%m%d') + '.log'

def resolve_file(f):
    return os.path.abspath(os.path.expanduser(f))

def get_ratio(n, d):
    t = '%1.1f%%'
    if d < 1:
        if n < 1:
            r = t % 0
        else:
            r = 'inf'
    else:
        r = t % ((float(n) / float(d)) * 100.0)
    return r

def homogenize(s):
    return s.replace(' ', '').lower().replace('\n', '').replace('\t', '')

def parse_player_name(name):
    ###
    # It's a little ridiculous, but people are VERY creative in how they
    # add their clan/team tags.  So we have a ridiculous algorithm to
    # figure this out.
    ###
    from ZDStack.Token import Token

    delimiters = {'[': ']', '<': '>', '(': ')', '*': '*', '_': '_',
                  '-': '-', ']': '[', '>': '<', ')': '(', ':': ':',
                  '=': '=', '.': '.', '^': '^'}
    seen = []
    waiting = []
    tokens = []
    s = ''
    other_stuff = ''
    in_token = False
    for c in name:
        if c in delimiters.keys(): # found a delimiter
            if waiting and waiting[-1] == c: # found the end of a token
                tokens.append(Token(s, seen[-1], c))
                s = ''
                waiting = waiting[:-1]
                seen = seen[:-1]
                in_token = False
            elif in_token: # found the beginning of a new token
                tokens.append(Token(s, seen[-1]))
                waiting = waiting[:-1]
                seen = seen[:-1]
                seen.append(c)
                s = ''
            else: # found the beginning of a token
                waiting = waiting[:-1]
                seen = seen[:-1]
                seen.append(c)
                waiting.append(delimiters[c])
                # other_stuff += c
                in_token = True
        elif in_token: # add to the current token
            s += c
        else: # not a token
            other_stuff += c
    if s:
        if in_token:
            tokens.append(Token(s, ''.join(seen)))
        else:
            other_stuff += s
    try:
        tokens = sorted([(len(t), t) for t in tokens])
        # tokens.reverse()
        token = tokens[0][1]
        tag = str(token)
        return (tag, name.replace(tag, ''))
    except IndexError: # no tag
        return (None, name)

def html_escape(s):
    # Basically ripped from web.py
    t = s.replace('&', "&amp;")
    t = t.replace('<', "&lt;")
    t = t.replace('>', "&gt;")
    t = t.replace("'", "&#39;")
    t = t.replace('"', "&quot;")
    return t

