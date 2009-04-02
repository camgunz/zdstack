###
#
# A lot of this code is ripped right out of SimpleXMLRPCServer.py included in
# the Python stdlib (version 2.5.2).  My reason for doing so is that simply
# changing the transport (from XML to JSON) is not possible doing simple
# subclassing, and this is clearer than monkeypatching.
#
# While I imagine this causes a license conflict, I am ignoring it because I
# could easily monkeypatch and avoid it.  If someone throws a fit I will
# change this :)
#
###

import datetime
import simplejson
import SocketServer

try:
    import fcntl
except ImportError:
    fcntl = None

from SimpleXMLRPCServer import SimpleXMLRPCDispatcher, \
                               SimpleXMLRPCRequestHandler
from ZDStack import RPCAuthenticationError

class AuthenticatedRPCDispatcher(SimpleXMLRPCDispatcher):

    def __init__(self, encoding, username, password):
        SimpleXMLRPCDispatcher.__init__(self, True, encoding)
        self.username = username
        self.password = password
        self.methods_requiring_authentication = set()

    def register_function(self, function, name=None,
                          requires_authentication=False):
        """Registers a function to respond to RPC requests.

        The optional name argument can be used to set a Unicode name
        for the function.

        """
        SimpleXMLRPCDispatcher.register_function(self, function, name=name)
        if requires_authentication:
            self.methods_requiring_authentication.add(name)

class BaseRPCRequestHandler(SimpleXMLRPCRequestHandler):

    def __init__(self, transport_mimetype):
        self.transport_mimetype = transport_mimetype

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
            self.send_header("Content-type", self.transport_mimetype)
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            # shut down the connection
            self.wfile.flush()
            self.connection.shutdown(1)

    def log_message(self, format, *args):
        logging.info("%s - - [%s] %s\n" % (self.address_string(),
                                           self.log_date_time_string(),
                                           format % args))

class XMLRPCRequestHandler(BaseRPCRequestHandler):

    def __init__(self):
        BaseRPCRequestHandler.__init__(self, 'text/xml')

class JSONRPCRequestHandler(BaseRPCRequestHandler):

    def __init__(self):
        BaseRPCRequestHandler.__init__(self, 'application/json')

class XMLRPCServer(SocketServer.TCPServer, AuthenticatedRPCDispatcher):

    allow_reuse_address = True

    def __init__(self, addr, username, password,
                 requestHandler=SimpleXMLRPCRequestHandler, logRequests=True,
                 encoding=None):
        self.logRequests = logRequests
        AuthenticatedRPCDispatcher.__init__(self, encoding, username, password)
        SocketServer.TCPServer.__init__(self, addr, requestHandler)
        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)

class JSONRPCServer(XMLRPCServer):

    def register_introspection_functions(self):
        XMLRPCServer.register_introspection_functions(self)
        self.func['system.describe'] = self.system_describe

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
