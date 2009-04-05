###
#
# A lot of this code is ripped right out of SimpleXMLRPCServer.py and
# xmlrpclib.py included in the Python stdlib (version 2.5.2).  My reason for
# doing so is that changing the transport (from XML to JSON) is not possible
# doing simple subclassing, and this is clearer than monkeypatching.
#
# While I imagine this causes a license conflict, I am ignoring it because I
# could easily monkeypatch and avoid it.  If someone throws a fit I will
# change this... although I hope they don't! :)
#
###

import logging
import datetime
import SocketServer

try:
    import fcntl
except ImportError:
    fcntl = None

from types import StringType
from SimpleXMLRPCServer import SimpleXMLRPCDispatcher, \
                               SimpleXMLRPCRequestHandler
from xmlrpclib import Fault, Transport, SafeTransport, ServerProxy, \
                      FastMarshaller, Marshaller, _Method

from ZDStack import RPCAuthenticationError, JSONNotFoundError, JSON_CLASS

json_class = None

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
        except Exception, e:
            ###
            # This should only happen if the module is buggy
            ###
            # internal error, report as HTTP server error
            import traceback
            es = "Error processing RPC request: %s\nTraceback:\n%s"
            logging.error(es % (e, traceback.format_exc()))
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
        if json_class is None:
            from ZDStack import JSON_CLASS as json_class
            if json_class is None:
                raise JSONNotFoundError
        try:
            try:
                logging.debug("Raw data: %s" % (data))
                d = json_class.loads(data)
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
        except Exception, e:
            import traceback
            traceback.print_exc()
            error = self.exception_to_dict(e, '000', 'Server error')
            return self.generate_response(None, error)
        return self.generate_response(result, None, id)

    def datetime_to_seconds(self, dt):
        ###
        # There's probably something in the 'time' module for this, but fuck
        # it.
        ###
        epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
        if type(dt) != type(epoch):
            raise TypeError("Cannot serialize [%s]" % (type(dt)))
        td = dt - epoch
        return (td.days * 86400) + td.seconds

    def generate_response(self, result=None, error=None, id=None):
        if json_class is None:
            from ZDStack import JSON_CLASS as json_class
            if json_class is None:
                raise JSONNotFoundError
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
        out = json_class.dumps(out, default=self.datetime_to_seconds)
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

class JSONTransport(Transport):

    def request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request
        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)
        self.send_request(h, handler, request_body)
        self.send_host(h, host)
        self.send_user_agent(h)
        self.send_content(h, request_body)
        errcode, errmsg, headers = h.getreply()
        if errcode != 200:
            raise ProtocolError(host + handler, errcode, errmsg, headers)
        self.verbose = verbose
        try:
            sock = h._conn.sock
        except AttributeError:
            sock = None

        return self._parse_response(h.getfile(), sock)
    def send_content(self, connection, request_body):
        connection.putheader("Content-Type", 'application/json')
        connection.putheader("Content-Length", str(len(request_body)))
        connection.endheaders()
        if request_body:
            connection.send(request_body)

    def _parse_response(self, file, sock):
        global json_class
        if json_class is None:
            from ZDStack import JSON_CLASS as json_class
            if json_class is None:
                raise JSONNotFoundError
        response = ''
        if sock:
            chunk = sock.recv(1024)
        else:
            chunk = file.read(1024)
        while chunk:
            response += chunk
            if sock:
                chunk = sock.recv(1024)
            else:
                chunk = file.read(1024)
        if self.verbose:
            print "body:", repr(response)
        file.close()
        return json_class.loads(response)

class SafeJSONTransport(JSONTransport):
    """Handles an HTTPS transaction to an XML-RPC server."""

    def make_connection(self, host):
        import httplib
        host, extra_headers, x509 = self.get_host_info(host)
        try:
            HTTPS = httplib.HTTPS
        except AttributeError:
            es = "your version of httplib doesn't support HTTPS"
            raise NotImplementedError(es)
        else:
            return HTTPS(host, None, **(x509 or {}))

class BaseProxy(ServerProxy):

    def __init__(self, uri, transport, encoding=None, verbose=0,
                       use_datetime=0):
        ServerProxy.__init__(self, uri, transport, encoding, verbose, True,
                                   True)

    def _secret_proxy_request_blag(self, methodname, params):
        req = self._secret_proxy_dumps_blag(params, methodname)
        resp = self.__transport.request(self.__host, self.__handler, req)
        if len(resp) == 1:
            resp = resp[0]
        return resp

    def _secret_get_request_func_blag(self):
        raise NotImplementedError

class XMLProxy:

    def __init__(self, uri, transport=None, encoding=None, verbose=0,
                       use_datetime=0):
        import urllib
        if transport is None:
            protocol, uri = urllib.splittype(uri)[0]
            if protocol == 'http':
                self.__transport = Transport(use_datetime)
            elif protocol == 'https':
                self.__transport = SafeTransport(use_datetime)
            else:
                raise IOError("unsupported XML-RPC protocol")
        else:
            self.__transport = transport
        self.__host, self.__handler = urllib.splithost(uri)
        self.__handler = self.__handler or '/RPC2'
        self.__encoding = encoding
        if self.__encoding == 'utf-8':
            xmlheader = "<?xml version='1.0'?>\n"
        else:
            xmlheader_template = "<?xml version='1.0' encoding='%s'?>\n"
            xmlheader = xmlheader_template % str(self.__encoding)
        if FastMarshaller:
            self.__marshaller = FastMarshaller(self.__encoding)
        else:
            self.__marshaller = Marshaller(self.__encoding, allow_none=True)
        method_call_template = \
            '%s<methodCall>\n<methodName>%%s</methodName>\n%%s</methodCall>'
        method_response_template = \
            '%s<methodResponse>\n%%s</methodResponse>'
        self.__method_call_template = method_call_template % (xmlheader)
        self.__method_response_template = method_response_template % (xmlheader)

    def __request(self, methodname, params):
        req = self.marshaller.dumps(params)
        if methodname:
            if not isinstance(methodname, StringType):
                methodname = methodname.encode(self.encoding)
            req = self.method_call_template % (methodname, req)
        resp = self.__transport.request(self.__host, self.__handler, req)
        if len(resp) == 1:
            resp = resp[0]
        return resp

    def __getattr__(self, name):
        # magic method dispatcher
        return _Method(self.__request, name)

    def __repr__(self):
        return ("<XMLServerProxy for %s%s>" % (self.__host, self.__handler))

    __str__ = __repr__

class JSONProxy:

    def __init__(self, uri, transport=None, encoding=None, verbose=0,
                       use_datetime=0):
        import urllib
        if transport is None:
            protocol, uri = urllib.splittype(uri)
            if protocol == 'http':
                self.__transport = JSONTransport(use_datetime)
            elif protocol == 'https':
                self.__transport = SafeJSONTransport(use_datetime)
            else:
                raise IOError("unsupported JSON-RPC protocol")
        else:
            self.__transport = transport
        self.__host, self.__handler = urllib.splithost(uri)
        self.__handler = self.__handler or '/RPC2'
        self.__encoding = encoding
        if self.__encoding == 'utf-8':
            xmlheader = "<?xml version='1.0'?>\n"
        else:
            xmlheader_template = "<?xml version='1.0' encoding='%s'?>\n"
            xmlheader = xmlheader_template % str(self.__encoding)
        if FastMarshaller:
            self.__marshaller = FastMarshaller(self.__encoding)
        else:
            self.__marshaller = Marshaller(self.__encoding, allow_none=True)
        method_call_template = \
            '%s<methodCall>\n<methodName>%%s</methodName>\n%%s</methodCall>'
        method_response_template = \
            '%s<methodResponse>\n%%s</methodResponse>'
        self.__method_call_template = method_call_template % (xmlheader)
        self.__method_response_template = method_response_template % (xmlheader)

    def __request(self, methodname, params):
        global json_class
        if json_class is None:
            from ZDStack import JSON_CLASS as json_class
            if json_class is None:
                raise JSONNotFoundError
        d = {'method': methodname, 'params': params, 'id': 'jsonrpc'}
        req = json_class.dumps(d)
        resp = self.__transport.request(self.__host, self.__handler, req)
        if len(resp) == 1:
            resp = resp[0]
        return resp

    def __getattr__(self, name):
        # magic method dispatcher
        return _Method(self.__request, name)

    def __repr__(self):
        return ("<JSONServerProxy for %s%s>" % (self.__host, self.__handler))

    __str__ = __repr__

