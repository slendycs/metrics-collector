import os

# Defaults keep module-level settings importable even when no `.env` file is present.
os.environ.setdefault("SERVER_NAME", "agent-test")
os.environ.setdefault("SERVER_TYPE", "test")
os.environ.setdefault("TIMEOUT_MIN", "1")
os.environ.setdefault("TIMEOUT_MAX", "2")
os.environ.setdefault("RECEPTION_SERVICE_URL", "http://reception.test")
os.environ.setdefault("LOG_LEVEL", "INFO")

# Fixtures are imported directly instead of via `pytest_plugins`: defining
# `pytest_plugins` in a non-top-level conftest is no longer supported by pytest.
from fixtures.agent import (  # noqa: E402,F401
    client,
    exporter,
    http_server,
    pooling_manager,
)
from fixtures.models import (  # noqa: E402,F401
    metrics,
    metrics_factory,
    server_stats,
    server_stats_factory,
)
