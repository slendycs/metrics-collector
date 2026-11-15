import os

# Intake settings are read at import time, so defaults are provided before any
# `intake` module is imported by the tests.
os.environ.setdefault("BUFFER_TYPE", "REDIS")
os.environ.setdefault("BUFFER_CAPACITY", "3")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6389/15")
os.environ.setdefault("LOG_LEVEL", "INFO")
