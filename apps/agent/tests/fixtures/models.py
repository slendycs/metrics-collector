from datetime import datetime
from typing import Any

import pytest

from models import Metrics, ServerStats
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
def server_stats_factory(metrics_factory):
    """Builds a ServerStats dataclass with overridable fields."""

    def factory(**overrides: Any) -> ServerStats:
        values: dict[str, Any] = {
            "server_name": "agent-1",
            "server_type": ServerTypes.TEST,
            "seq": 1,
            "metrics": metrics_factory(),
        }
        values.update(overrides)
        return ServerStats(**values)

    return factory


@pytest.fixture
def server_stats(server_stats_factory):
    return server_stats_factory()
