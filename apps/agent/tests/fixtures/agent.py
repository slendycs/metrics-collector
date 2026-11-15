import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast

import pytest

from agent.client import Client
from agent.exporter import MetricsExporter
from agent.manager import PoolingManager


@pytest.fixture
def exporter():
    return MetricsExporter()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def pooling_manager():
    return PoolingManager()


class _TestServer(ThreadingHTTPServer):
    """ThreadingHTTPServer that records received requests."""

    requests: list[dict[str, object]] = []
    response_status: int = 200


class _RecordingHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length)
        server = cast(_TestServer, self.server)
        server.requests.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "json": json.loads(raw_body),
            }
        )
        self.send_response(server.response_status)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, format, *args):  # noqa: A002 - required signature
        pass


@pytest.fixture
def http_server():
    """Runs a real local HTTP server and exposes the requests it received."""
    server = _TestServer(("127.0.0.1", 0), _RecordingHandler)
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
