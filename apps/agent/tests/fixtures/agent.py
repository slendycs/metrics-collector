import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from client import Client
from exporter import MetricsExporter
from manager import PoolingManager


@pytest.fixture
def exporter():
    return MetricsExporter()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def pooling_manager():
    return PoolingManager()


class _RecordingHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length)
        self.server.requests.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "json": json.loads(raw_body),
            }
        )
        self.send_response(getattr(self.server, "response_status", 200))
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, format, *args):  # noqa: A002 - required signature
        pass


@pytest.fixture
def http_server():
    """Runs a real local HTTP server and exposes the requests it received."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _RecordingHandler)
    server.requests = []
    server.response_status = 200
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
