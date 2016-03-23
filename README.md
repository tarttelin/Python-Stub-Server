# Stub Server


[![travis build](https://api.travis-ci.org/tarttelin/Python-Stub-Server.svg)](https://travis-ci.org/tarttelin/Python-Stub-Server)

[![coverage](https://coveralls.io/repos/tarttelin/Python-Stub-Server/badge.svg?branch=master&service=github)](https://coveralls.io/github/tarttelin/Python-Stub-Server?branch=master)

## Web Server stub

Testing external web dependencies in a mock objects style. Thanks to great contributions this
library now supports Python 2.5 upto Python 3.4 (not yet tested with 3.5). There are a comprehensive suite of tests 
in the test.py file, which serve both as the TDD tests written while creating this library, and as examples / documentation.  
It supports any HTTP method, i.e. GET, PUT, POST and DELETE.  It supports chunked encoding, but
currently we have no use cases for multipart support etc, so it doesn't do it.
An excerpt from the tests is below:


```python
  from unittest import TestCase
  from stubserver import StubServer

  class WebTest(TestCase):

      def setUp(self):
          self.server = StubServer(8998)
          self.server.run()

      def tearDown(self):
          self.server.stop()
          # implicitly calls verify on stop

      def test_put_with_capture(self):
          capture = {}
          self.server.expect(method="PUT", url="/address/\d+$", data_capture=capture)\
                     .and_return(reply_code=201)

          # do stuff here
          captured = eval(capture["body"])
          self.assertEquals("world", captured["hello"])
```

The stub server has been used extensively over the last 6 years by various teams and is considered stable. 

## FTP Stub Server

There have been some great contributions to the FTP Stub Server. It is now a reasonably capable FTP server but does
not support all FTP commands. There are tests showing usage in the test.py file.

## Get it from PyPi

You can install it with pip by running:

```python
pip install stubserver
```