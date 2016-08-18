import unittest
import sys
from io import BytesIO
from ftplib import FTP
from stubserver import StubServer, FTPStubServer
from unittest import TestCase
if sys.version_info[0] < 3:
    from urllib2 import OpenerDirector, HTTPHandler, Request
else:
    from urllib.request import OpenerDirector, HTTPHandler, Request


class WebTest(TestCase):
    def setUp(self):
        self.server = StubServer(8998)
        self.server.run()

    def tearDown(self):
        self.server.stop()
        self.server.verify()  # this is redundant because stop includes verify

    def _make_request(self, url, method="GET", payload="", headers={}):
        self.opener = OpenerDirector()
        self.opener.add_handler(HTTPHandler())
        request = Request(url, headers=headers, data=payload.encode('utf-8'))
        request.get_method = lambda: method
        response = self.opener.open(request)
        response_code = getattr(response, 'code', -1)
        return (response, response_code)

    def test_get_with_file_call(self):
        with open('data.txt', 'w') as f: 
            f.write("test file")
        self.server.expect(method="GET", url="/address/\d+$").and_return(mime_type="text/xml", file_content="./data.txt")
        response, response_code = self._make_request("http://localhost:8998/address/25", method="GET")
        with open("./data.txt", "r") as f:
            expected = f.read().encode('utf-8')
        try:
            self.assertEqual(expected, response.read())
        finally:
            response.close()
        
    def test_put_with_capture(self):
        capture = {}
        self.server.expect(method="PUT", url="/address/\d+$", data_capture=capture).and_return(reply_code=201)
        f, reply_code = self._make_request("http://localhost:8998/address/45", method="PUT", payload=str({"hello": "world", "hi": "mum"}))
        try:
            self.assertEqual(b"", f.read())
            captured = eval(capture["body"])
            self.assertEqual("world", captured["hello"])
            self.assertEqual("mum", captured["hi"])
            self.assertEqual(201, reply_code)
        finally:
            f.close()

    def test_post_with_wrong_data(self):
        self.server.expect(method="POST", url="data/", data='Bob').and_return()
        f, reply_code = self._make_request("http://localhost:8998/data/", method="POST", payload='Chris')
        self.assertEqual(403, reply_code)
        self.assertRaises(Exception, self.server.stop)

    def test_post_with_multiple_expectations_wrong_data(self):
        self.server.expect(method="POST", url="data/", data='Bob').and_return(reply_code=201)
        self.server.expect(method="POST", url="data/", data='John').and_return(reply_code=202)
        self.server.expect(method="POST", url="data/", data='Dave').and_return(reply_code=203)
        f, reply_code = self._make_request("http://localhost:8998/data/", method="POST", payload='Dave')
        self.assertEqual(203, reply_code)
        f, reply_code = self._make_request("http://localhost:8998/data/", method="POST", payload='Bob')
        self.assertEqual(201, reply_code)
        f, reply_code = self._make_request("http://localhost:8998/data/", method="POST", payload='Chris')
        self.assertEqual(403, reply_code)
        self.assertRaises(Exception, self.server.stop)

    def test_post_with_mixed_expectations(self):
        self.server.expect(method="POST", url="data/").and_return(reply_code=202)
        self.server.expect(method="POST", url="data/", data='John').and_return(reply_code=201)
        f, reply_code = self._make_request("http://localhost:8998/data/", method="POST", payload='John')
        self.assertEqual(201, reply_code)
        f, reply_code = self._make_request("http://localhost:8998/data/", method="POST", payload='Dave')
        self.assertEqual(202, reply_code)

    def test_post_with_data_and_no_body_response(self):
        self.server.expect(method="POST", url="address/\d+/inhabitant", data='<inhabitant name="Chris"/>').and_return(reply_code=204)
        f, reply_code = self._make_request("http://localhost:8998/address/45/inhabitant", method="POST", payload='<inhabitant name="Chris"/>')
        self.assertEqual(204, reply_code)

    def test_multiple_expectations_identifies_correct_unmatched_request(self):
        self.server.expect(method="POST", url="address/\d+/inhabitant", data='Twas brillig and the slithy toves').and_return(reply_code=204)
        f, reply_code = self._make_request("http://localhost:8998/address/45/inhabitant", method="POST", payload='Twas brillig and the slithy toves')
        self.assertEqual(204, reply_code)
        self.server.expect(method="GET", url="/monitor/server_status$").and_return(content="Four score and seven years ago", mime_type="text/html")
        try:
            self.server.stop()
        except Exception as e:
            self.assertEqual(-1, str(e).find('brillig'), str(e))

    def test_get_with_data(self):
        self.server.expect(method="GET", url="/monitor/server_status$").and_return(content="<html><body>Server is up</body></html>", mime_type="text/html")
        f, reply_code = self._make_request("http://localhost:8998/monitor/server_status", method="GET")
        try:
            self.assertTrue(b"Server is up" in f.read())
            self.assertEqual(200, reply_code)
        finally:
            f.close()

    def test_get_from_root(self):
        self.server.expect(method="GET", url="/$").and_return(content="<html><body>Server is up</body></html>", mime_type="text/html")
        f, reply_code = self._make_request("http://localhost:8998/", method="GET")
        try:
            self.assertTrue(b"Server is up" in f.read())
            self.assertEqual(200, reply_code)
        finally:
            f.close()

    def test_put_when_post_expected(self):
        # set expectations
        self.server.expect(method="POST", url="address/\d+/inhabitant", data='<inhabitant name="Chris"/>').and_return(
            reply_code=204)

        # try a different method
        f, reply_code = self._make_request("http://localhost:8998/address/45/inhabitant", method="PUT",
                                           payload='<inhabitant name="Chris"/>')

        # Validate the response
        self.assertEqual("Method not allowed", f.msg)
        self.assertEqual(405, reply_code)
        self.assertTrue(f.read().startswith(b"Method PUT not allowed."))

        # And we have an unmet expectation which needs to mention the POST that didn't happen
        try:
            self.server.stop()
        except Exception as e:
            self.assertTrue(str(e).find("POST") > 0, str(e))

    def test_unexpected_get(self):
        f, reply_code = self._make_request("http://localhost:8998/address/45/inhabitant", method="GET")
        self.assertEqual(404, reply_code)
        self.server.stop()

    def test_repeated_get(self):
        self.server.expect(method="GET", url="counter$").and_return(content="1")
        self.server.expect(method="GET", url="counter$").and_return(content="2")
        self.server.expect(method="GET", url="counter$").and_return(content="3")

        for i in range(1, 4):
            f, reply_code = self._make_request("http://localhost:8998/counter", method="GET")
            self.assertEqual(200, reply_code)
            self.assertEqual(str(i).encode('utf-8'), f.read())

    def test_extra_get(self):
        self.server.expect(method="GET", url="counter$").and_return(content="1")
        f, reply_code = self._make_request("http://localhost:8998/counter", method="GET")
        self.assertEqual(200, reply_code)
        self.assertEqual(b"1", f.read())

        f, reply_code = self._make_request("http://localhost:8998/counter", method="GET")
        self.assertEqual(400, reply_code)
        self.assertEqual("Expectations exhausted",f.msg)
        self.assertTrue(f.read().startswith(b"Expectations at this URL have already been satisfied.\n"))


class FTPTest(TestCase):
    def setUp(self):
        self.server = FTPStubServer(0)
        self.server.run()
        self.port = self.server.server.server_address[1]
        self.ftp = FTP()
        self.ftp.set_debuglevel(0)
        self.ftp.connect('localhost', self.port)
        self.ftp.login('user1', 'passwd')
        
    def tearDown(self):
        self.ftp.quit()
        self.ftp.close()
        self.server.stop()

    def test_change_directory(self):
        self.ftp.cwd('newdir')
        self.assertEqual(self.ftp.pwd(), 'newdir')

    def test_put_test_file(self):
        self.assertFalse(self.server.files("foo.txt"))
        self.ftp.storlines('STOR foo.txt', BytesIO(b'cant believe its not bitter'))
        self.assertTrue(self.server.files("foo.txt"))

    def test_put_2_files_associates_the_correct_content_with_the_correct_filename(self):
        data = "\n".join(["file1 content" for i in range(1024)])
        self.ftp.storlines('STOR robot.txt', BytesIO(data.encode('utf-8')))
        self.ftp.storlines('STOR monster.txt', BytesIO(b'file2 content'))
        self.assertEqual("\r\n".join(["file1 content" for i in range(1024)]),
                          self.server.files("robot.txt").strip())
        self.assertEqual("file2 content", self.server.files("monster.txt").strip())

    def test_list_2_files(self):
        self.lines = []
        def accumulate(line):
            self.lines.append(line)

        self.ftp.storlines('STOR palladium.csv', BytesIO(b'data'))
        self.ftp.storlines('STOR vanadiyam.pdf', BytesIO(b'more data'))
        self.ftp.retrlines('LIST', accumulate)
        self.assertEqual(sorted(self.lines), sorted(['vanadiyam.pdf', 'palladium.csv']))

    def test_nlst_2_files(self):
        self.lines = []
        def accumulate(line):
            self.lines.append(line)

        self.ftp.storlines('STOR palladium.csv', BytesIO(b'data'))
        self.ftp.storlines('STOR vanadiyam.pdf', BytesIO(b'more data'))
        self.ftp.retrlines('NLST', accumulate)
        self.assertEqual(sorted(self.lines), sorted(['vanadiyam.pdf', 'palladium.csv']))

    def test_retrieve_expected_file_returns_file(self):
        expected_content = 'content of my file\nis a complete mystery to me.'
        self.server.add_file('foo.txt', expected_content)
        directory_content = []
        self.ftp.retrlines('LIST', lambda x: directory_content.append(x))
        file_content = []
        self.ftp.retrlines('RETR foo.txt', lambda x: file_content.append(x))
        self.assertTrue('foo.txt' in '\n'.join(directory_content))
        self.assertEqual(expected_content, '\n'.join(file_content))


class VerifyTest(TestCase):
    def setUp(self):
        self.server = StubServer(8998)

    def test_verify_checks_all_expectations(self):
        satisfied_expectation = self._MockExpectation(True)
        unsatisfied_expectation = self._MockExpectation(False)
        self.server._expectations = [
            satisfied_expectation,
            unsatisfied_expectation,
            satisfied_expectation
        ]

        self.assertRaises(Exception, self.server.verify)

    def test_verify_clears_all_expectations(self):
        satisfied_expectation = self._MockExpectation(True)
        self.server._expectations = [
            satisfied_expectation,
            satisfied_expectation,
            satisfied_expectation
        ]

        self.server.verify()

        self.assertEqual([], self.server._expectations)

    class _MockExpectation(object):
        def __init__(self, satisfied):
            self.satisfied = satisfied


if __name__=='__main__':
    unittest.main()
