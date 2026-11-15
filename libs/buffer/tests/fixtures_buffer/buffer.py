import os
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from redis.exceptions import RedisError

from buffer import RedisBuffer
from models import Bid, Metrics
from models.enums import ServerTypes


DEFAULT_REDIS_URL = "redis://127.0.0.1:6389/15"


@pytest.fixture
def redis_url() -> str:
    return os.environ.get("TEST_REDIS_URL", DEFAULT_REDIS_URL)


@pytest.fixture
def metrics_factory():
    """Builds a Metrics dataclass with overridable fields."""

    def factory(**overrides: Any) -> Metrics:
        values: dict[str, Any] = {
            "cpu_load": 12.5,
            "ram_load": 43.2,
            "disk_read": 1024,
            "disk_write": 512,
            "load_average": [0.1, 0.2, 0.3],
            "timestamp": datetime(2026, 1, 1, 12, 0, 0),
        }
        values.update(overrides)
        return Metrics(**values)

    return factory


@pytest.fixture
def bid_factory(metrics_factory):
    """Builds a Bid dataclass with overridable fields."""

    def factory(**overrides: Any) -> Bid:
        values: dict[str, Any] = {
            "source_name": "agent-1",
            "source_type": ServerTypes.TEST,
            "seq": 7,
            "time_in": datetime(2026, 1, 1, 12, 0, 0),
            "stats": metrics_factory(),
            "id": None,
        }
        values.update(overrides)
        return Bid(**values)

    return factory


@pytest.fixture
def bid(bid_factory):
    return bid_factory()


@pytest.fixture
def scripts():
    """Mocks of the Lua scripts registered on the Redis client."""
    return {
        "put_bid": AsyncMock(),
        "return_bid": AsyncMock(),
        "take_next": AsyncMock(),
    }


@pytest.fixture
def fake_redis(scripts):
    """Redis client mock that returns the prepared script mocks."""
    client = MagicMock()
    client.ping = AsyncMock()
    client.aclose = AsyncMock()
    client.register_script.side_effect = [
        scripts["put_bid"],
        scripts["return_bid"],
        scripts["take_next"],
    ]
    return client


@pytest.fixture
def redis_buffer(fake_redis):
    return RedisBuffer(fake_redis, capacity=3)


@pytest_asyncio.fixture
async def real_redis(redis_url):
    """Connection to a real Redis test database, skipped when Redis is down."""
    client = aioredis.from_url(redis_url, decode_responses=True)
    try:
        await client.ping()
    except RedisError as err:
        await client.aclose()
        pytest.skip(f"Redis is unavailable at {redis_url}: {err}")

    await client.flushdb()
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest.fixture
def real_buffer_factory(real_redis):
    """Creates RedisBuffer instances sharing the real Redis connection."""

    def factory(capacity: int) -> RedisBuffer:
        return RedisBuffer(real_redis, capacity)

    return factory


@pytest_asyncio.fixture
async def real_redis_client_factory(real_redis, redis_url):
    """Creates independent Redis clients after confirming Redis is available.

    Depends on ``real_redis`` so the test is skipped when Redis is down. Each
    client uses its own connection pool, keeping the shared ``real_redis``
    teardown intact.
    """
    clients: list[aioredis.Redis] = []

    def factory() -> aioredis.Redis:
        client = aioredis.from_url(redis_url, decode_responses=True)
        clients.append(client)
        return client

    try:
        yield factory
    finally:
        for client in clients:
            try:
                await client.aclose()
            except RedisError:
                pass
