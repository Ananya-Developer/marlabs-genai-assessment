"""Loopback-only internal HTTP service. The public trust boundary is Spring Boot."""
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from core import Engine, Failure

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
engine = Engine(timeout=float(os.getenv("MODEL_TIMEOUT_SECONDS", "1")))


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 24 * 1024 * 1024:
                self.reply(400, {"error": {"code": "INVALID_INTERNAL_REQUEST", "message": "Invalid request size."}})
                return
            payload = json.loads(self.rfile.read(size))
            if self.path == "/answer":
                response = engine.answer(payload["context"], payload["question"], payload["as_of"])
            elif self.path == "/batch":
                response = engine.batch(payload)
            else:
                self.reply(404, {"error": {"code": "NOT_FOUND", "message": "Unknown endpoint."}})
                return
            self.reply(200, response)
        except Failure as error:
            self.reply(504 if error.code == "MODEL_TIMEOUT" else 502, {"error": {"code": error.code, "message": error.message}})
        except Exception:
            self.reply(502, {"error": {"code": "INTERNAL_FAILURE", "message": "Processing service failed."}})

    def reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass  # No document contents or headers in logs.


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(os.getenv("PYTHON_PORT", "8001"))), Handler).serve_forever()
