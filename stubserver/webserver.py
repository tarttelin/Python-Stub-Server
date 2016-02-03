import BaseHTTPServer, cgi, threading, re, urllib
import time
import sys


class StoppableHTTPServer(BaseHTTPServer.HTTPServer):
    """
    Python 2.5 HTTPServer does not close down properly when calling server_close.
    The implementation below was based on the comments in the below article:
    http://stackoverflow.com/questions/268629/how-to-stop-basehttpserver-serveforever-in-a-basehttprequesthandler-subclass
    """
    stopped = False
    allow_reuse_address = True

    def __init__(self, *args, **kw):
        BaseHTTPServer.HTTPServer.__init__(self, *args, **kw)

    def serve_forever(self):
        while not self.stopped:
            self.handle_request()

    def server_close(self):
        BaseHTTPServer.HTTPServer.server_close(self)
        self.stopped = True
        self._create_dummy_request()
        time.sleep(0.5)

    def shutdown(self):
        pass

    def _create_dummy_request(self):
        f = urllib.urlopen("http://localhost:" + str(self.server_port) + "/__shutdown")
        f.read()
        f.close()


if sys.version_info < (2, 6):
    HTTPServer = StoppableHTTPServer
else:
    HTTPServer = BaseHTTPServer.HTTPServer


class StubServer(object):
    def __init__(self, port=8080, address='localhost'):
        self._expectations = []
        self.port = port
        self.address = address

    def run(self):
        server_address = (self.address, self.port)
        self.httpd = HTTPServer(server_address, StubResponse(self._expectations))
        thread = threading.Thread(target=self._run)
        thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.verify()

    def _run(self):
        try:
            self.httpd.serve_forever()
        except:
            pass

    def verify(self):
        """
        Check all exceptation has been made.

        :raises: Exception: If one them isn't made.
        """
        failures = []
        for expectation in self._expectations:
            if not expectation.satisfied:
                failures.append(str(expectation))
        del self._expectations[:]
        if failures:
            raise Exception("Unsatisfied expectations: " + "\n".join(failures))

    def expect(self, method="GET", url="^UrlRegExpMather$", data=None, data_capture={},
               file_content=None):
        """
        Prepare :class:`StubServer` to handle an HTTP request.

        :param method: HTTP method
        :type method: ``str``

        :param url: Regex matching with path part of an URL
        :type url: Raw ``str``

        :param data: Excepted data
        :type data: ``None`` or other

        :param data_capture: Dictionary given by user for gather data returned
                             by server.
        :type data_capture: ``dict``

        :param file_content: Unsed

        :return: Expectation object initilized
        :rtype: :class:`Expectation`
        """
        expected = Expectation(method, url, data, data_capture)
        self._expectations.append(expected)
        return expected


class Expectation(object):
    def __init__(self, method, url, data, data_capture):
        """
        :param method: HTTP method
        :type method: ``str``

        :param url: Regex matching with path part of an URL
        :type url: ``str``

        :param data: Excepted data
        :type data: ``None`` or other

        :param data_capture: Dictionary given by user for gather data returned
                             by server.
        :type data_capture: ``dict``
        """
        self.method = method
        self.url = url
        self.data = data
        self.data_capture = data_capture
        self.satisfied = False

    def and_return(self, mime_type="text/html", reply_code=200, content="", file_content=None):
        """
        Define the response created by the expectation.

        :param mime_type: Define content type of HTTP response
        :type mime_type: ``str``

        :param reply_code: Define response code of HTTP response
        :type reply_code: ``int``

        :param content: Define response's content
        :type content: ``str``

        :param file_content: Define response's content from a file
        :type file_content: ``str``
        """
        if file_content:
            f = open(file_content, "r")
            content = f.read()
            f.close()
        self.response = (reply_code, mime_type, content)

    def __str__(self):
        return "url: %s \n data_capture: %s\n" % (self.url, self.data_capture)


class StubResponse(BaseHTTPServer.BaseHTTPRequestHandler):

    def __call__(self, request, client_address, server):
        self.request = request
        self.client_address = client_address
        self.server = server
        try:
            self.setup()
            self.handle()
        finally:    
            self.finish()

    def __init__(self, expectations):
        self.expected = expectations

    def _get_data(self):
        max_chunk_size = 10*1024*1024
        if not self.headers.has_key("content-length"):
            return ""
        size_remaining = int(self.headers["content-length"])
        L = []
        while size_remaining:
            chunk_size = min(size_remaining, max_chunk_size)
            L.append(self.rfile.read(chunk_size))
            size_remaining -= len(L[-1])
        return ''.join(L)

    def handle_one_request(self):
        """Handle a single HTTP request.

        You normally don't need to override this method; see the class
        __doc__ string for information on how to handle specific HTTP
        commands such as GET and POST.
        """
        self.raw_requestline = self.rfile.readline()
        if not self.raw_requestline:
            self.close_connection = 1
            return
        if not self.parse_request(): # An error code has been sent, just exit
            return
        method = self.command
        if self.path == "/__shutdown":
            self.send_response(200, "Python")
        for exp in self.expected:
            if exp.method == method and re.search(exp.url, self.path) and not exp.satisfied:
                self.send_response(exp.response[0], "Python")
                self.send_header("Content-Type", exp.response[1])
                self.end_headers()
                self.wfile.write(exp.response[2])
                data = self._get_data()
                exp.satisfied = True
                exp.data_capture["body"] = data
                break
        self.wfile.flush()

    def log_request(code=None, size=None):
        pass
