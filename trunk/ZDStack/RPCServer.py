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

import sys
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

from ZDStack import RPCAuthenticationError, get_json_module, get_zdslog, \
                    get_debugging

zdslog = get_zdslog()

class AuthenticatedRPCDispatcher(SimpleXMLRPCDispatcher):

    """Adds authentication to RPC dispatching.

    .. attribute:: encoding
        A string representing the encoding of the RPC data.
    .. attribute:: username
        A string representing the authenticating username
    .. attribute:: password
        A string representing the authenticating password

    """

    def __init__(self, encoding, username, password):
        zdslog.debug('')
        SimpleXMLRPCDispatcher.__init__(self, True, encoding)
        self.username = username
        self.password = password
        self.methods_requiring_authentication = set()

    def register_function(self, function, name=None,
                          requires_authentication=False):
        """Registers a function to respond to RPC requests.

        :param function: the function to register
        :type function: function
        :param name: the name to register the function under; uses the
                     function's current name by default.
        :type name: string
        :param requires_authentication: whether or not the function
                                        requires authentication.
        :type requires_authentication: boolean

        """
        # zdslog.debug('')
        name = name or function.__name__
        self.funcs[name] = function
        if requires_authentication:
            self.methods_requiring_authentication.add(name)

    def _dispatch(self, method, params):
        """Dispatches an RPC call.

        :param method: the name of the function to call
        :type method: string
        :param params: the arguments to pass to method
        :type params: list

        """
        requires_auth = method in self.methods_requiring_authentication
        s = 'Dispatching %s, requires_authentication: %s'
        zdslog.debug(s % (method, requires_auth))
        if requires_auth:
            if not len(params) >= 2:
                raise RPCAuthenticationError('<no_username_given>')
            username, password, params = params[0], params[1], params[2:]
            if (username, password) != (self.username, self.password):
                es = "Auth failed for %s/%s: %s/%s"
                zdslog.debug(es % (username, password, self.username,
                                    self.password))
                raise RPCAuthenticationError(username)
        return SimpleXMLRPCDispatcher._dispatch(self, method, params)

class BaseRPCRequestHandler(SimpleXMLRPCRequestHandler):

    """BaseRPCRequestHandler allows a configurable transport MIME-Type."""

    def __init__(self, transport_mimetype):
        zdslog.debug('')
        self.transport_mimetype = transport_mimetype

    def do_POST(self):
        """Handles the HTTP POST request.

        Attempts to interpret all HTTP POST requests as JSON-RPC calls,
        which are forwarded to the server's _dispatch method for handling.
        """
        zdslog.debug('')
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
            zdslog.debug("After _marshaled_dispatch")
        except Exception, e:
            ###
            # This should only happen if the module is buggy
            ###
            # internal error, report as HTTP server error
            import traceback
            es = "Error processing RPC request: %s\nTraceback:\n%s"
            s = es % (e, traceback.format_exc())
            zdslog.error(s)
            # self.send_response(500)
            ###
            # This is just for debugging.
            ###
            self.send_response(200)
            self.send_header("Content-type", self.transport_mimetype)
            self.send_header("Content-length", str(len(s)))
            self.end_headers()
            self.wfile.write(s)
            # shut down the connection
            self.wfile.flush()
            self.connection.shutdown(1)
            self.end_headers()
        else:
            # got a valid JSON RPC response
            self.send_response(200)
            es = "Sending Content-Type header: %s"
            logging.debug(es % (self.transport_mimetype))
            es = "Sending Content-Length header: %s"
            logging.debug(es % (str(len(response))))
            self.send_header("Content-type", self.transport_mimetype)
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            # shut down the connection
            self.wfile.flush()
            self.connection.shutdown(1)

    def log_message(self, format, *args):
        """Logs a message

        :param format: a format string
        :type format: string
        :param args: the arguments to interpolate into the format
                     string
        :type args: list

        """
        zdslog.debug('')
        zdslog.info("%s - - [%s] %s\n" % (self.address_string(),
                                           self.log_date_time_string(),
                                           format % args))

class XMLRPCRequestHandler(BaseRPCRequestHandler):

    """XMLRPCRequestHandler handles XML-RPC requests."""

    def __init__(self):
        zdslog.debug('')
        BaseRPCRequestHandler.__init__(self, 'text/xml')

class JSONRPCRequestHandler(BaseRPCRequestHandler):

    """JSONRPCRequestHandler handles JSON-RPC requests."""
    def __init__(self):
        zdslog.debug('')
        BaseRPCRequestHandler.__init__(self, 'application/json')

class XMLRPCServer(SocketServer.TCPServer, AuthenticatedRPCDispatcher):

    allow_reuse_address = True

    def __init__(self, addr, username, password,
                 requestHandler=SimpleXMLRPCRequestHandler, logRequests=True,
                 encoding=None):
        zdslog.debug('')
        self.logRequests = logRequests
        AuthenticatedRPCDispatcher.__init__(self, encoding, username, password)
        SocketServer.TCPServer.__init__(self, addr, requestHandler)
        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)

class JSONRPCServer(XMLRPCServer):

    def register_introspection_functions(self):
        zdslog.debug('')
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
        zdslog.debug('_marshaled_dispatch(%s, %s' % (data, dispatch_method))
        try:
            try:
                # zdslog.debug("Raw data: %s" % (data))
                d = get_json_module().loads(data)
            except Exception, e:
                if get_debugging():
                    import traceback
                    tb = traceback.format_exc()
                else:
                    tb = 'Parse Error'
                error = self.exception_to_dict(e, '000', tb)
                return self.generate_response(None, error)
            if not 'method' in d:
                zdslog.debug("No method given in RPC request")
                error = self.exception_to_dict(Exception('Bad Call'), '000', '')
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
            if get_debugging():
                import traceback
                tb = traceback.format_exc()
            else:
                tb = 'Server Error'
            error = self.exception_to_dict(e, '000', tb)
            return self.generate_response(None, error)
        return self.generate_response(result, None, id)

    def datetime_to_seconds(self, dt):
        """Converts a datetime instance into seconds since the epoch.

        :param dt: the datetime instance
        :type dt: datetime

        """
        ###
        # There's probably something in the 'time' module for this, but fuck
        # it.
        ###
        zdslog.debug('')
        epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
        if type(dt) != type(epoch):
            raise TypeError("Cannot serialize [%s]" % (type(dt)))
        td = dt - epoch
        return (td.days * 86400) + td.seconds

    def generate_response(self, result=None, error=None, id=None):
        """Generates a JSON response.

        :param result: the output of the RPC method call
        :param error: error information
        :type error: dict
        :param id: the id number of the request
        :type id: integer

        """
        zdslog.debug('')
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
        out = get_json_module().dumps(out, default=self.datetime_to_seconds)
        zdslog.debug("Returning %s" % (out))
        return out

    def exception_to_dict(self, e, code, context):
        """Converts an exception into a serializable dict.

        :param e: an exception to convert
        :type e: exception
        :param code: the 3-digit error code
        :type code: string
        :context: a message to go along with the exception
        :type context: string

        """
        zdslog.debug('')
        out = {}
        out['name'] = "JSONRPCError"
        out['code'] = code
        out['message'] = context
        out['error'] = {'name': str(type(e)).strip('<>')[6:-1],
                        'message': str(e)}
        return out

    def set_summary(self, summary):
        """Sets this server's summary.
        
        :param summary: the summary to set
        :type summary: string
        
        """
        zdslog.debug('')
        self.summary = summary

    def set_help_url(self, help_url):
        """Sets this server's help URL.
        
        :param help_url: the help URL
        :type help_url: string
        
        """
        zdslog.debug('')
        self.help_url = help_url

    def set_address(self, address):
        """Sets this server's address.
        
        :param address: the address to set
        :type address: string
        
        """
        zdslog.debug('')
        self.address = address

    def system_describe(self):
        """system.describe() => {'sdversion': '1.0', 'name': ...}"""
        zdslog.debug('')
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

    ###
    # def request(self, host, handler, request_body, verbose=0):
    #     # issue XML-RPC request
    #     h = self.make_connection(host)
    #     if verbose:
    #         h.set_debuglevel(1)
    #     self.send_request(h, handler, request_body)
    #     self.send_host(h, host)
    #     self.send_user_agent(h)
    #     self.send_content(h, request_body)
    #     errcode, errmsg, headers = h.getreply()
    #     if errcode != 200:
    #         raise ProtocolError(host + handler, errcode, errmsg, headers)
    #     self.verbose = verbose
    #     try:
    #         sock = h._conn.sock
    #     except AttributeError:
    #         sock = None
    #     return self._parse_response(h.getfile(), sock)
    ###

    def send_content(self, connection, request_body):
        zdslog.debug('')
        connection.putheader("Content-Type", 'application/json')
        connection.putheader("Content-Length", str(len(request_body)))
        connection.endheaders()
        if request_body:
            connection.send(request_body)

    def _parse_response(self, file, sock):
        zdslog.debug('')
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
        return get_json_module().loads(response)

class SafeJSONTransport(JSONTransport):
    """Handles an HTTPS transaction to an XML-RPC server."""

    def make_connection(self, host):
        zdslog.debug('')
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
        zdslog.debug('')
        ServerProxy.__init__(self, uri, transport, encoding, verbose, True,
                                   True)

class XMLProxy(object):

    def __init__(self, uri, transport=None, encoding=None, verbose=0,
                       use_datetime=0):
        zdslog.debug('')
        import urllib
        protocol, uri = urllib.splittype(uri)
        if transport is None:
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
        self.__encoding = encoding or 'utf-8'
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
        zdslog.debug('')
        req = self.__marshaller.dumps(params)
        if methodname:
            if not isinstance(methodname, StringType):
                methodname = methodname.encode(self.__encoding)
            req = self.__method_call_template % (methodname, req)
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

class JSONProxy(object):

    def __init__(self, uri, transport=None, encoding=None, verbose=0,
                       use_datetime=0):
        zdslog.debug('')
        import urllib
        protocol, uri = urllib.splittype(uri)
        if transport is None:
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
        zdslog.debug('')
        d = {'method': methodname, 'params': params, 'id': 'jsonrpc'}
        req = get_json_module().dumps(d)
        response = self.__transport.request(self.__host, self.__handler, req)
        if len(response) == 1:
            response = response[0]
        ###
        # A response looks like this:
        #
        # {'result': None, 'error': None, 'version': '1.1', 'id': None}
        #
        ###
        if response['error']:
            ###
            # An error looks like this:
            #
            # {'name': 'JSONRPCError',
            #  'code': '000',                      # or something
            #  'message': 'Parse Error',           # or something
            #  'error': {'name': 'AttributeError', # or something
            #            'message': '"blah" has no ".name" attribute'}}
            #
            # Yes, this ends up looking ridiculous.
            #
            ###
            ###
            # Could probably do better than 'Exception' here...
            ###
            es = "Received error [%s]: %s - %s\nError name: %s\nError "
            es += "message: %s"
            raise Exception(es % (response['error']['code'],
                                  response['error']['name'],
                                  response['error']['message'],
                                  response['error']['error']['name'],
                                  response['error']['error']['message']))
        else:
            return response['result']

    def __getattr__(self, name):
        # magic method dispatcher
        return _Method(self.__request, name)

    def __repr__(self):
        return ("<JSONServerProxy for %s%s>" % (self.__host, self.__handler))

    __str__ = __repr__

