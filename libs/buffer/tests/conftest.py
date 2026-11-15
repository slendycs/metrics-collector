# Fixtures are imported directly instead of via `pytest_plugins`: defining
# `pytest_plugins` in a non-top-level conftest is no longer supported by pytest.
from fixtures_buffer.buffer import (  # noqa: E402,F401
    bid,
    bid_factory,
    fake_redis,
    metrics_factory,
    real_buffer_factory,
    real_redis,
    real_redis_client_factory,
    redis_buffer,
    redis_url,
    scripts,
)
