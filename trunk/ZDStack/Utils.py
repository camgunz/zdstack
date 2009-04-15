from __future__ import with_statement

import sys
import os.path

from datetime import datetime, timedelta

def check_ip(ip):
    tokens = ip.split('.')
    if not len(tokens) == 4:
        raise ValueError("Malformed IP Address")
    try:
        int_tokens = [int(t) for t in tokens]
    except:
        raise ValueError("Malformed IP Address")
    for t in int_tokens:
        if t < 0 or t > 255:
            raise ValueError("Malformed IP Address")
    if tokens[3] == 0 or tokens[3] == 255:
        es = "Cannot advertise a broadcast IP address to master"
        raise ValueError(es)
    if tokens[0] == 10 or \
       (tokens[0] == 172 and tokens[1] in range(16, 32)) or \
       (tokens[0] == 192 and tokens[1] == 168):
         es = "Cannot advertise a private IP address to master"
         raise ValueError(es)

def timedelta_in_seconds(x):
    """Returns the value of a time delta in seconds as an int."""
    return (x.days * 86400) + x.seconds

def get_logfile_suffix(roll=False):
    """Returns today's logfile suffix.

    roll:  a boolean that, if given, does the following:
            - If the time is 11pm, generates a logfile name for the
              upcoming day.
           Otherwise, the name generated is for the current day.

    """
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)
    if roll and now.hour == 23:
        today += timedelta(days=1)
    return today.strftime('-%Y%m%d') + '.log'

def resolve_path(f):
    """Returns the expanded, absolute path of a given file/folder.

    f: a path to expand.

    """
    return os.path.abspath(os.path.expanduser(f))

def get_ratio(n, d):
    """Returns a ratio as a string percentage.

    n: numerator
    d: denominator

    """
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
    """Homogenizes a string.

    s: a string to homogenize

    """
    return s.replace(' ', '').lower().replace('\n', '').replace('\t', '')

def parse_player_name(name):
    """Parses a player's name into a tag and a base player name.

    name: a string representing the player name to parse

    """
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
    """Escapes HTML.

    s: a string representing a string to escape

    This function is basically ripped from web.py, with any luck,
    the MIT and BSD licenses are compatible... :)  I don't think
    Mr. Swartz would have a cow, tho.

    """
    t = s.replace('&', "&amp;")
    t = t.replace('<', "&lt;")
    t = t.replace('>', "&gt;")
    t = t.replace("'", "&#39;")
    t = t.replace('"', "&quot;")
    return t

###
# I'm not a huge fan of eval, but it's so easy I can't resist.
###

def send_proxy_method(proxy, method_name, *args):
    """Sends an RPC request, returning the result or printing an error.

    proxy:       an RPC proxy instance, either JSON or XML
    method_name: a string representing the name of the method to
                 remotely execute.
    *args:       a *expanded list of arguments to pass to the method
                 specified by method_name.

    If an error occurs, it will be printed to STDERR.  This is because
    this method is primarily for use by scripts trying to interact
    with a running ZDStack.

    """
    try:
        return eval("proxy." + method_name + "(*args)")
    except Exception, e:
        if not hasattr(e, 'traceback') and not hasattr(e, 'error'):
            raise
        else:
            if hasattr(e, 'error'):
                try:
                    print >> sys.stderr, "\n%s: %s\n" % (e.error['name'],
                                                         e.error['message'])
                    if 'traceback' in e.error:
                        print >> sys.stderr, e.error['traceback']
                except:
                    raise e
            else:
                raise

def get_event_from_line(line, regexps, now=None):
    """Returns a LogEvent from a line.

    line:    the line from which to return an event - a string.
    regexps: a sequence of Regexp instances which will be used to
             parse the line.
    now:     an optional datetime instance that will be used for the
             event's event_dt parameter.  If not given, 'now()' is
             used.

    """
    now = now or datetime.now()
    e = None
    for r in regexps:
        e = r.get_event(line, now)
        if e:
            break
    if e:
        if e.category == 'frag':
            e.data['weapon'] = e.type
        elif e.category == 'death':
            e.data.update({'fragger': e.data['fraggee'], 'weapon': e.type})
        elif e.category == 'join':
            if 'team' in e.data:
                e.data['team'] = e.data['team'].lower()
        if e.type == 'map_change':
            e.data['number'] = int(e.data['number'])
    return e

def requires_lock(lck):
    ###
    # Owes pretty heavily to Philip J. Eby's article on function decorators.
    ###
    def decorator(f):
        def wrapper(*__args, **__kwargs):
            __can_skip_lock = False
            if 'acquire_lock' in __kwargs:
                __can_skip_lock = not __kwargs['acquire_lock']
                del __kwargs['acquire_lock']
            if not __can_skip_lock:
                with lck:
                    return f(*__args, **__kwargs)
            else:
                return f(*__args, **__kwargs)
        wrapper.__name__ = f.__name__
        wrapper.__dict__ = f.__dict__
        wrapper.__doc__ = f.__doc__
        return wrapper
    return decorator

def requires_instance_lock():
    def decorator(f):
        def wrapper(self, *__args, **__kwargs):
            __can_skip_lock = False
            if 'acquire_lock' in __kwargs:
                __can_skip_lock = not __kwargs['acquire_lock']
                del __kwargs['acquire_lock']
            if not __can_skip_lock:
                with self.lock:
                    return f(self, *__args, **__kwargs)
            else:
                return f(self, *__args, **__kwargs)
        wrapper.__name__ = f.__name__
        wrapper.__dict__ = f.__dict__
        wrapper.__doc__ = f.__doc__
        return wrapper
    return decorator

