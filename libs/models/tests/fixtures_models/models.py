from datetime import datetime
from typing import Any

import pytest

from models import Bid, Metrics, PutResult
from models.enums import ServerTypes


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
def metrics(metrics_factory):
    return metrics_factory()


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
def put_result_factory():
    """Builds a PutResult dataclass with overridable fields."""

    def factory(**overrides: Any) -> PutResult:
        values: dict[str, Any] = {
            "accepted": True,
            "slot": 1,
            "bid_id": 42,
            "seq": 7,
        }
        values.update(overrides)
        return PutResult(**values)

    return factory


@pytest.fixture
def put_result(put_result_factory):
    return put_result_factory()
