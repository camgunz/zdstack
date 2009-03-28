"""Simple JSON-RPC Server.

This module can be used to create simple JSON-RPC servers
by creating a server and either installing functions, a
class instance, or by extending the SimpleJSONRPCServer
class.

A list of possible usage patterns follows:

1. Install functions:

server = SimpleJSONRPCServer(("localhost", 8000))
server.register_function(pow)
server.register_function(lambda x,y: x+y, 'add')
server.serve_forever()

2. Install an instance:

class MyFuncs:
    def __init__(self):
        # make all of the string functions available through
        # string.func_name
        import string
        self.string = string
    def _listMethods(self):
        # implement this method so that system.listMethods
        # knows to advertise the strings methods
        return list_public_methods(self) + \
                ['string.' + method for method in list_public_methods(self.string)]
    def pow(self, x, y): return pow(x, y)
    def add(self, x, y) : return x + y

server = SimpleJSONRPCServer(("localhost", 8000))
server.register_introspection_functions()
server.register_instance(MyFuncs())
server.serve_forever()

3. Install an instance with custom dispatch method:

class Math:
    def _listMethods(self):
        # this method must be present for system.listMethods
        # to work
        return ['add', 'pow']
    def _methodHelp(self, method):
        # this method must be present for system.methodHelp
        # to work
        if method == 'add':
            return "add(2,3) => 5"
        elif method == 'pow':
            return "pow(x, y[, z]) => number"
        else:
            # By convention, return empty
            # string if no help is available
            return ""
    def _dispatch(self, method, params):
        if method == 'pow':
            return pow(*params)
        elif method == 'add':
            return params[0] + params[1]
        else:
            raise 'bad method'

server = SimpleJSONRPCServer(("localhost", 8000))
server.register_introspection_functions()
server.register_instance(Math())
server.serve_forever()

4. Subclass SimpleJSONRPCServer:

class MathServer(SimpleJSONRPCServer):
    def _dispatch(self, method, params):
        try:
            # We are forcing the 'export_' prefix on methods that are
            # callable through JSON-RPC to prevent potential security
            # problems
            func = getattr(self, 'export_' + method)
        except AttributeError:
            raise Exception('method "%s" is not supported' % method)
        else:
            return func(*params)

    def export_add(self, x, y):
        return x + y

server = MathServer(("localhost", 8000))
server.serve_forever()

Note that this server is certainly not up to the JSON-RPC spec.  This
is due to the fact that I (Charlie) changed this in 2 hours, scattered
over 15-minute increments.  Over time, I'm sure it will become more
compliant, and less like I just changed the _marshaled_dispatch
method.

"""

# Switched from XML to JSON by Charlie Gunyon (charles.gunyon@gmail.com).
# Written by Brian Quinlan (brian@sweetapp.com).
# Based on code written by Fredrik Lundh.

import datetime
import simplejson
import SocketServer
import BaseHTTPServer
import sys
import os
try:
    import fcntl
except ImportError:
    fcntl = None

def resolve_dotted_attribute(obj, attr, allow_dotted_names=True):
    """resolve_dotted_attribute(a, 'b.c.d') => a.b.c.d

    Resolves a dotted attribute name to an object.  Raises
    an AttributeError if any attribute in the chain starts with a '_'.

    If the optional allow_dotted_names argument is false, dots are not
    supported and this function operates similar to getattr(obj, attr).
    """
    for i in [attr]:
        if i.startswith('_'):
            raise AttributeError('attempt to access private attribute "%s"' % i)
        else:
            obj = getattr(obj,i)
    return obj

def list_public_methods(obj):
    """Returns a list of attribute strings, found in the specified
    object, which represent callable attributes"""
    return [member for member in dir(obj)
                if not member.startswith('_') and
                    callable(getattr(obj, member))]

def remove_duplicates(lst):
    """remove_duplicates([2,2,2,1,3,3]) => [3,1,2]

    Returns a copy of a list without duplicates. Every list
    item must be hashable and the order of the items in the
    resulting list is not defined.
    """
    u = {}
    for x in lst:
        u[x] = 1
    return u.keys()

class ProcedureNotFoundError(Exception):
    """Raised when a non-existent procedure is called."""
    def __init__(self, method_name):
        Exception.__init__(self, "Procedure not found: [%s]" % (method_name))

class SimpleJSONRPCDispatcher:
    """Mix-in class that dispatches JSON-RPC requests.

    This class is used to register JSON-RPC method handlers
    and then to dispatch them. There should never be any
    reason to instantiate this class directly.
    """

    def __init__(self):
        self.funcs = {}
        self.instance = None

    def register_instance(self, instance):
        """Registers an instance to respond to JSON-RPC requests.

        Only one instance can be installed at a time.

        If the registered instance has a _dispatch method then that
        method will be called with the name of the JSON-RPC method and
        its parameters as a tuple or a dict (depending upon whether
        arguments were specified using position or naming,
        respectively), e.g. instance._dispatch('add',(2,3))

        If the registered instance does not have a _dispatch method
        then the instance will be searched to find a matching method
        and, if found, will be called. Methods beginning with an '_'
        are considered private and will not be called by
        SimpleJSONRPCServer.

        If a registered function matches a JSON-RPC request, then it
        will be called instead of the registered instance.

        Dotted names are not supported.  There's a couple of ways
        around this that are actually secure, as opposed to using
        dotted names... which isn't.

        """
        self.instance = instance
        self.allow_dotted_names = allow_dotted_names

    def register_function(self, function, name=None):
        """Registers a function to respond to JSON-RPC requests.

        The optional name argument can be used to set a Unicode name
        for the function.

        """
        if name is None:
            name = function.__name__
        self.funcs[name] = function

    def register_introspection_functions(self):
        """Registers the JSON-RPC introspection methods in the system
        namespace.

        We also register a couple of holdovers from XML-RPC.

        """
        fd = {'system.listMethods': self.system_listMethods,
              'system.methodSignature': self.system_methodSignature,
              'system.methodHelp': self.system_methodHelp,
              'system.describe': self.system_describe}
        self.funcs.update(fd)

    def _marshaled_dispatch(self, data, dispatch_method=None):
        """Dispatches an JSON-RPC method from marshalled (JSON) data.

        JSON-RPC methods are dispatched from the marshalled (JSON) data
        using the _dispatch method and the result is returned as
        marshalled data. For backwards compatibility, a dispatch
        function can be provided as an argument (see comment in
        SimpleJSONRPCRequestHandler.do_POST) but overriding the
        existing method through subclassing is the prefered means
        of changing method dispatch behavior.

        """
        try:
            try:
                d = simplejson.loads(data)
            except Exception, e:
                import traceback
                traceback.print_exc()
                error = self.exception_to_dict(e, '000', 'Parse error')
                return self.generate_response(None, error)
            # print >> sys.stderr, "Received %s" % (str(d))
            if not 'method' in d:
                error = {'name': 'JSONRPCError', 'code': '000',
                         'message': 'Bad Call'}
                return self.generate_response(None, error)
            id, params = (None, [])
            if 'id' in d:
                id = d['id']
            if 'params' in d:
                params = d['params']
            if dispatch_method is not None:
                result = dispatch_method(d['method'], params)
            else:
                result = self._dispatch(d['method'], params)
        except ProcedureNotFoundError, pnfe:
            import traceback
            traceback.print_exc()
            error = self.exception_to_dict(pnfe, '000', 'Procedure not found')
            return self.generate_response(None, error)
        except Exception, e:
            import traceback
            traceback.print_exc()
            error = self.exception_to_dict(e, '000', 'Server error')
            return self.generate_response(None, error)
        return self.generate_response(result, None, id)

    def datetime_to_seconds(self, dt):
        epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
        if type(dt) != type(epoch):
            raise TypeError("Cannot serialize [%s]" % (type(td)))
        td = dt - epoch
        return (td.days * 86400) + td.seconds

    def generate_response(self, result=None, error=None, id=None):
        # print >> sys.stderr, "generate_response got %s, %s, %s" % (result,
                                                                   # error, id)
        out = {'result': None, 'error': None, 'version': '1.1', 'id': None}
        assert not (result is not None and error is not None)
        if result is not None:
            out['result'] = result
        if error is not None:
            out['error'] = error
        if id is not None:
            out['id'] = id
        out = simplejson.dumps(out, default=self.datetime_to_seconds)
        # print >> sys.stderr, "Returning %s" % (out)
        return out

    def exception_to_dict(self, e, code, context):
        out = {}
        out['name'] = "JSONRPCError"
        out['code'] = code
        out['message'] = context
        out['error'] = {'name': str(type(e)).strip('<>')[6:-1],
                        'message': str(e)}
        return out

    def set_summary(self, summary):
        """Sets this server's summary."""
        self.summary = summary

    def set_help_url(self, help_url):
        """Sets this server's help URL."""
        self.help_url = help_url

    def set_address(self, address):
        """Sets this server's address."""
        self.address = address

    def system_describe(self):
        """system.describe() => {'sdversion': '1.0', 'name': ...}"""
        out = {}
        out['sdversion'] == '1.0'
        out['name'] == self.name
        address = ':'.join([str(x) for x in self.server.server_address])
        out['id'] == 'http://' + address
        if hasattr(self, 'summary') and self.summary:
            out['summary'] == self.summary
        if hasattr(self, 'help_url') and self.help_url:
            out['help'] == self.help_url
        if hasattr(self, 'address') and self.address:
            out['address'] == self.address
        return out

    def system_listMethods(self):
        """system.listMethods() => ['add', 'subtract', 'multiple']

        Returns a list of the methods supported by the server.
        
        """
        methods = self.funcs.keys()
        if self.instance is not None:
            # Instance can implement _listMethod to return a list of
            # methods
            if hasattr(self.instance, '_listMethods'):
                methods = remove_duplicates(
                        methods + self.instance._listMethods()
                    )
            # if the instance has a _dispatch method then we
            # don't have enough information to provide a list
            # of methods
            elif not hasattr(self.instance, '_dispatch'):
                methods = remove_duplicates(
                        methods + list_public_methods(self.instance)
                    )
        methods.sort()
        return methods

    def system_methodSignature(self, method_name):
        """system.methodSignature('add') => [double, int, int]

        Returns a list describing the signature of the method. In the
        above example, the add method takes two integers as arguments
        and returns a double result.

        This server does NOT support system.methodSignature.
        
        """
        return 'signatures not supported'

    def system_methodHelp(self, method_name):
        """system.methodHelp('add') => "Adds two integers together"

        Returns a string containing documentation for the specified method.

        """
        method = None
        if self.funcs.has_key(method_name):
            method = self.funcs[method_name]
        elif self.instance is not None:
            # Instance can implement _methodHelp to return help for a method
            if hasattr(self.instance, '_methodHelp'):
                return self.instance._methodHelp(method_name)
            # if the instance has a _dispatch method then we
            # don't have enough information to provide help
            elif not hasattr(self.instance, '_dispatch'):
                try:
                    method = resolve_dotted_attribute(
                                self.instance,
                                method_name,
                                self.allow_dotted_names
                                )
                except AttributeError:
                    pass

        # Note that we aren't checking that the method actually
        # be a callable object of some kind
        if method is None:
            return ""
        else:
            import pydoc
            return pydoc.getdoc(method)

    def _dispatch(self, method, params):
        """Dispatches the JSON-RPC method.

        JSON-RPC calls are forwarded to a registered function that
        matches the called JSON-RPC method name. If no such function
        exists then the call is forwarded to the registered instance,
        if available.

        If the registered instance has a _dispatch method then that
        method will be called with the name of the JSON-RPC method and
        its parameters as a tuple
        e.g. instance._dispatch('add',(2,3))

        If the registered instance does not have a _dispatch method
        then the instance will be searched to find a matching method
        and, if found, will be called.

        Methods beginning with an '_' are considered private and will
        not be called.

        """
        func = None
        try:
            # check to see if a matching function has been registered
            func = self.funcs[method]
        except KeyError:
            if self.instance is not None:
                # check for a _dispatch method
                if hasattr(self.instance, '_dispatch'):
                    return self.instance._dispatch(method, params)
                else:
                    # call instance method directly
                    try:
                        func = resolve_dotted_attribute(self.instance, method)
                    except AttributeError:
                        pass
        if func is not None:
            if isinstance(params, list):
                return func(*params)
            elif isinstance(params, dict):
                return func(**params)
        else:
            raise ProcedureNotFoundError(method)

class SimpleJSONRPCRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Simple JSON-RPC request handler class.

    Handles all HTTP POST requests and attempts to decode them as
    JSON-RPC requests.

    """
    # Class attribute listing the accessible path components;
    # paths not on this list will result in a 404 error.
    rpc_paths = ()

    def is_rpc_path_valid(self):
        if self.rpc_paths:
            return self.path in self.rpc_paths
        else:
            # If .rpc_paths is empty, just assume all paths are legal
            return True

    def do_POST(self):
        """Handles the HTTP POST request.

        Attempts to interpret all HTTP POST requests as JSON-RPC calls,
        which are forwarded to the server's _dispatch method for handling.
        """

        # Check that the path is legal
        if not self.is_rpc_path_valid():
            self.report_404()
            return

        try:
            # Get arguments by reading body of request.
            # We read this in chunks to avoid straining
            # socket.read(); around the 10 or 15Mb mark, some platforms
            # begin to have problems (bug #792570).
            max_chunk_size = 10*1024*1024
            size_remaining = int(self.headers["content-length"])
            L = []
            while size_remaining:
                chunk_size = min(size_remaining, max_chunk_size)
                L.append(self.rfile.read(chunk_size))
                size_remaining -= len(L[-1])
            data = ''.join(L)

            # In previous versions of SimpleJSONRPCServer, _dispatch
            # could be overridden in this class, instead of in
            # SimpleJSONRPCDispatcher. To maintain backwards compatibility,
            # check to see if a subclass implements _dispatch and dispatch
            # using that method if present.
            response = self.server._marshaled_dispatch(
                    data, getattr(self, '_dispatch', None)
                )
        except Exception, e: # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.end_headers()
        else:
            # got a valid JSON RPC response
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

            # shut down the connection
            self.wfile.flush()
            self.connection.shutdown(1)

    def report_404 (self):
            # Report a 404 error
        self.send_response(404)
        response = 'No such page'
        self.send_header("Content-type", "text/plain")
        self.send_header("Content-length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
        # shut down the connection
        self.wfile.flush()
        self.connection.shutdown(1)

    def log_request(self, code='-', size='-'):
        """Selectively log an accepted request."""

        if self.server.logRequests:
            BaseHTTPServer.BaseHTTPRequestHandler.log_request(self, code, size)

class SimpleJSONRPCServer(SocketServer.TCPServer, SimpleJSONRPCDispatcher):
    """Simple JSON-RPC server.

    Simple JSON-RPC server that allows functions and a single instance
    to be installed to handle requests. The default implementation
    attempts to dispatch JSON-RPC calls to the functions or instance
    installed in the server. Override the _dispatch method inhereted
    from SimpleJSONRPCDispatcher to change this behavior.
    """

    allow_reuse_address = True

    def __init__(self, addr, requestHandler=SimpleJSONRPCRequestHandler,
                 logRequests=True):
        self.logRequests = logRequests

        SimpleJSONRPCDispatcher.__init__(self)
        SocketServer.TCPServer.__init__(self, addr, requestHandler)

        # [Bug #1222790] If possible, set close-on-exec flag; if a
        # method spawns a subprocess, the subprocess shouldn't have
        # the listening socket open.
        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)

if __name__ == '__main__':
    print 'Running JSON-RPC server on port 8000'
    server = SimpleJSONRPCServer(("localhost", 8000))
    server.register_function(pow)
    server.register_function(lambda x,y: x+y, 'add')
    server.register_introspection_functions()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
