from __future__ import with_statement

import os
import sys
import stat
import decimal
import logging

zdslog = logging.getLogger('ZDStack')

from datetime import datetime, timedelta

def create_file(filepath):
    """Creates a file with proper permissions.

    :param filepath: the full path to the file to create
    :type filepath: string

    """
    open(filepath, 'w').close()
    os.chmod(filepath, stat.S_IRWXU)

def check_ip(ip):
    """Checks that a string is a properly formed IP address.

    :param ip: the string to check
    :type ip: string

    Raises an Exception if the IP address is malformed.  This method
    also raises an Exception if the address is either a broadcast or
    private address.

    """
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
    if tokens[3] in(0, 255):
        es = "Cannot advertise a broadcast IP address to master"
        raise ValueError(es)
    if tokens[0] == 10 or \
       (tokens[0] == 172 and tokens[1] in range(16, 32)) or \
       (tokens[0] == 192 and tokens[1] == 168):
         es = "Cannot advertise a private IP address to master"
         raise ValueError(es)

def timedelta_in_seconds(td):
    """Converts a timedelta into seconds.
    
    :param td: a timedelta to convert
    :type td: timedelta
    :rtype: int
    
    """
    return (td.days * 86400) + td.seconds

def resolve_path(f):
    """Resolves a path.

    :param f: a path to resolve
    :type f: string
    :rtype: string
    :returns: The expanded, absolute path of a given file/folder.

    """
    return os.path.abspath(os.path.expanduser(f))

def homogenize(s):
    """Homogenizes a string.

    :param s: a string to homogenize
    :type s: string
    :rtype: string
    :returns: a homogenized string, with spaces, newlines, and tabs
              removed

    """
    return s.replace(' ', '').lower().replace('\n', '').replace('\t', '')

def parse_player_name(name):
    """Parses a player's name into a tag and a base player name.

    :param name: the raw name to parse
    :type name: string
    :rtype: a 2-Tuple of strings
    :returns: ('tag', 'name')

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

    :param s: a string to escape
    :type s: string
    :rtype: string
    :returns: an escaped string

    This function is basically ripped from web.py; with any luck,
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

    :param proxy: an RPC proxy, either JSON or XML
    :type proxy: XMLProxy or JSONProxy
    :param method_name: the name of the method to remotely execute
    :type method_name: string
    :param args: other positional arguments to pass to the RPC method

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
    """Gets a :class:`~ZDStack.LogEvent.LogEvent` from a line.

    :param line: the line from which to return an event
    :type line: string
    :param regexps: the regexps with which to parse the line
    :type regexps: list of compiled regexp instances
    :param now: the time to use for the event's event_dt parameter, if
                not given, datetime.datetime.now() is used.
    :type now: datetime
    :returns: a :class:`~ZDStack.LogEvent.LogEvent` parsed from the
              given line or None
    :rtype: :class:`~ZDStack.LogEvent.LogEvent`

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
        if 'team' in e.data:
            e.data['team'] = e.data['team'].lower()
        if e.type == 'map_change' and 'number' in e.data:
            e.data['number'] = int(e.data['number'])
    else:
        e = LogEvent(now, 'junk', {}, 'junk', line)
    return e

def requires_lock(lck):
    """A function decorator that acquires a lock before executing.

    :param lck: the :class:`~threading.Lock` that the function requires
    :type lck: :class:`~threading.Lock`

    """
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
                zdslog.debug('Acquiring %s in %s' % (lck, f.__name__))
                with lck:
                    zdslog.debug('Acquired %s in %s' % (lck, f.__name__))
                    output = f(*__args, **__kwargs)
                zdslog.debug('Released %s' % (lck))
                return output
            else:
                zdslog.debug('Skipping acquisition of %s' % (lck))
                return f(*__args, **__kwargs)
        wrapper.__name__ = f.__name__
        wrapper.__dict__ = f.__dict__
        wrapper.__doc__ = f.__doc__
        return wrapper
    return decorator

def requires_instance_lock():
    """Like requires_lock, but it acquires its parent's instance lock.

    This function decorator works on instance methods, acquiring their
    parent instance's lock before executing.

    """
    def decorator(f):
        def wrapper(self, *__args, **__kwargs):
            __can_skip_lock = False
            if 'acquire_lock' in __kwargs:
                __can_skip_lock = not __kwargs['acquire_lock']
                del __kwargs['acquire_lock']
            if not __can_skip_lock:
                zdslog.debug('Acquiring %s in %s' % (self.lock, f.__name__))
                with self.lock:
                    zdslog.debug('Acquired %s in %s' % (self.lock, f.__name__))
                    output = f(self, *__args, **__kwargs)
                zdslog.debug('Released %s' % (self.lock))
                return output
            else:
                return f(self, *__args, **__kwargs)
        wrapper.__name__ = f.__name__
        wrapper.__dict__ = f.__dict__
        wrapper.__doc__ = f.__doc__
        return wrapper
    return decorator

def parse_ban_line(line):
    """Converts a properly formatted string into a \
:class:`~ZDStack.ZDSAccessList.Ban`

    :param line: a line to convert
    :type line: string
    :rtype: :class:`~ZDStack.ZDSAccessList.Ban`

    """
    from ZDStack.ZDSAccessList import Ban
    if '#' in line:
        ip_address, reason = line.strip().split('#')
    else:
        ip_address, reason = (line.strip(), None)
    return Ban(ip_address, reason)

