import threading
import sys

if sys.version_info[0] < 3:
    import SocketServer
else:
    import socketserver as SocketServer


class FTPServer(SocketServer.BaseRequestHandler):
    def __init__(self, hostname, port, interactions, files):
        self.hostname = hostname
        self.port = port
        self.interactions = interactions
        self.files = files
        self.cwd = '/'

    def __call__(self, request, client_address, server):
        self.request = request
        self.client_address = client_address
        self.server = server
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()
        return self

    def handle(self):
        # Establish connection
        self.request.send(b'220 (FtpStubServer 0.1a)\r\n')
        self.communicating = True
        while self.communicating:
            cmd = self.request.recv(1024)
            if len(cmd) == 0:
                break
            if cmd:
                self.interactions.append(cmd)
                cmd = cmd.decode('utf-8').rstrip()
                first = cmd.split(' ', 1)[0]
                getattr(self, '_' + first)(cmd)

    def _USER(self, cmd):
        self.request.send(b'331 Please specify password.\r\n')

    def _PASS(self, cmd):
        self.request.send(b'230 You are now logged in.\r\n')

    def _TYPE(self, cmd):
        self.request.send(b'200 Switching to ascii mode.\r\n')

    def _PASV(self, cmd):
        self.data_handler = FTPDataServer(self.files)
        self.port += 1
        SocketServer.TCPServer.allow_reuse_address = True
        self.data_server = SocketServer.TCPServer((self.hostname, self.port + 1), self.data_handler)
        self.request.send(('227 Entering Passive Mode. (127,0,0,1,%s,%s)\r\n' % (
            int((self.port + 1) / 256), (self.port + 1) % 256)).encode('utf-8'))

    def child_go(self, action):
        self.data_handler.set_action(action)
        self.data_server.handle_request()
        self.data_server.server_close()

    def _STOR(self, cmd):
        filename = cmd.split(' ', 2)[1]
        self.data_handler.set_filename(filename)
        self.request.send(b'150 Okay to send data\r\n')
        self.child_go('STOR')
        self.request.send(b'226 Got the file\r\n')

    def _LIST(self, cmd):
        self.request.send(b'150 Accepted data connection\r\n')
        self.child_go('LIST')
        self.request.send(b'226 You got the listings now\r\n')

    def _RETR(self, cmd):
        filename = cmd.split(' ', 2)[1]
        self.data_handler.set_filename(filename)
        self.request.send(b'150 Accepted data connection\r\n')
        self.child_go('RETR')
        self.request.send(b'226 Enjoy your file\r\n')

    def _CWD(self, cmd):
        self.cwd = cmd.split(' ', 2)[1]
        self.request.send(('250 OK. Current directory is "%s"\r\n' % self.cwd).encode('utf-8'))

    def _PWD(self, cmd):
        self.request.send(('257 "%s" is your current location\r\n' % self.cwd).encode('utf-8'))

    def _NLST(self, cmd):
        self.request.send(b'150 Accepted data connection\r\n')
        self.child_go('NLST')
        self.request.send(b'226 You got the listings now\r\n')

    def _QUIT(self, cmd):
        self.communicating = False
        self.request.send(b'221-Goodbye.\r\n221 Have fun.')


class FTPDataServer(SocketServer.StreamRequestHandler):
    def __init__(self, files):
        self.files = files
        self.command = 'LIST'

    def __call__(self, request, client_address, server):
        self.request = request
        self.client_address = client_address
        self.server = server
        self.setup()
        try:
            self.handle()
            return self
        finally:
            self.finish()

    def set_action(self, action):
        self.action = action

    def handle(self):
        getattr(self, '_' + self.action)()

    def set_filename(self, filename):
        self.filename = filename.encode('utf-8')

    def _STOR(self):
        self.files[self.filename] = self.rfile.read().strip()

    def _LIST(self):
        data = b'\n'.join([name for name in self.files.keys()])
        self.wfile.write(data)

    def _NLST(self):
        data = b'\015\012'.join([name for name in self.files.keys()])
        self.wfile.write(data)

    def _RETR(self):
        self.wfile.write(self.files[self.filename])


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass


class FTPStubServer(object):
    def __init__(self, port, hostname='localhost'):
        self.hostname = hostname
        self.port = port
        self._interactions = []
        self._files = {}

    def files(self, name):
        name = name.encode('utf-8')
        if name in self._files:
            return self._files[name].decode('utf-8')
        return None

    def add_file(self, name, content):
        self._files[name.encode('utf-8')] = content.encode('utf-8')

    def run(self, timeout=2):
        self.handler = FTPServer(self.hostname, self.port, self._interactions, self._files)
        self.server = ThreadedTCPServer((self.hostname, self.port), self.handler)

        # Retrieving actual port when using a random one.
        if self.port == 0:
            self.port = self.server.server_address[1]
            self.handler.port = self.port

        server_thread = threading.Thread(target=self.server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()

    def stop(self):
        self.server.shutdown()
        while self._interactions:
            self._interactions.pop()
        while self._files:
            self._files.popitem()
