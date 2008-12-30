from DocXMLRPCServer import DocXMLRPCServer, DocXMLRPCRequestHandler

class XMLRPCServer(DocXMLRPCServer):

    def __init__(self, addr):
        DocXMLRPCServer.__init__(self, addr, logRequests=True)
        self.register_introspection_functions()
        self.allow_none = True
        self.set_server_title('ZDStack')
        self.set_server_name('ZDStack XML-RPC API')
        self.set_server_documentation("""\
This is the documentation for the ZDStack XML-RPC API.  For more information, visit
http://zdstack.googlecode.com.""")

    def log_message(self, format, *args):
        logging.info("%s - - [%s] %s\n" % (self.address_string(),
                                           self.log_date_time_string(),
                                           format % args))

