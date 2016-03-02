"""A stub webserver used to enable blackbox testing of applications that call
external web urls. For example, an application that consumes data from an
external REST api. The usage pattern is intended to be very much like using
a mock framework."""
from stubserver.webserver import StubServer
from stubserver.ftpserver import FTPStubServer

VERSION = __version__ = '0.3.3'
__author__ = 'Chris Tarttelin and Point 2 inc'
__email__ = 'chris@pyruby.co.uk'
__url__ = 'http://www.pyruby.com/pythonstubserver'
