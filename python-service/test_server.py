import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import server
from core import Engine
from test_core import Spy, ATLAS, DAY

class ServerTests(unittest.TestCase):
    def test_model_errors_are_non_2xx(self):
        original=server.engine
        http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        worker=threading.Thread(target=http.serve_forever,daemon=True); worker.start()
        try:
            for mode,expected,code in [('timeout',504,'MODEL_TIMEOUT'),('unavailable',502,'MODEL_UNAVAILABLE'),('malformed',502,'MODEL_MALFORMED')]:
                with self.subTest(mode=mode):
                    spy=Spy(mode); server.engine=Engine(model=spy,timeout=.01)
                    request=Request(f'http://127.0.0.1:{http.server_port}/answer',data=json.dumps({'context':ATLAS,'question':'certification','as_of':DAY}).encode(),headers={'Content-Type':'application/json'})
                    with self.assertRaises(HTTPError) as caught: urlopen(request,timeout=2)
                    self.assertEqual(caught.exception.code,expected)
                    self.assertEqual(json.load(caught.exception)['error']['code'],code)
                    self.assertEqual(len(spy.calls),1)
        finally:
            http.shutdown(); http.server_close(); worker.join(); server.engine=original

if __name__=='__main__': unittest.main()
