import os

# Defaults keep module-level settings importable even when no `.env` file is present.
os.environ.setdefault("SERVER_NAME", "agent-test")
os.environ.setdefault("SERVER_TYPE", "test")
os.environ.setdefault("TIMEOUT_MIN", "1")
os.environ.setdefault("TIMEOUT_MAX", "2")
os.environ.setdefault("RECEPTION_SERVICE_URL", "http://reception.test")
os.environ.setdefault("LOG_LEVEL", "INFO")

pytest_plugins = [
    "fixtures.models",
    "fixtures.agent",
]
