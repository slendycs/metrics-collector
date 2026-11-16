from datetime import datetime

import pytest

from buffer import Buffer
from models import PutResult, ServerStatsDTO, ServerTypes
from models.metrics import MetricsDTO


@pytest.fixture
def metrics_dto() -> MetricsDTO:
    """Метрики сервера в виде DTO, как их прислал бы агент."""
    return MetricsDTO(
        cpu_load=12.5,
        ram_load=43.2,
        disk_read=1024,
        disk_write=512,
        load_average=[0.1, 0.2, 0.3],
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def server_stats_dto(metrics_dto) -> ServerStatsDTO:
    """Пакет метрик источника, который принимает маршрут /collect."""
    return ServerStatsDTO(
        server_name="agent-1",
        server_type=ServerTypes.TEST,
        seq=7,
        metrics=metrics_dto,
    )


@pytest.fixture
def server_stats_payload(server_stats_dto) -> dict:
    """JSON-представление пакета метрик для запроса к ASGI-приложению."""
    return server_stats_dto.model_dump(mode="json")


class StubBuffer(Buffer):
    """Буфер-заглушка: записывает вызовы put и умеет вернуть результат или ошибку."""

    def __init__(
        self,
        result: PutResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = (
            result
            if result is not None
            else PutResult(accepted=True, bid_id=1, seq=0, slot=1)
        )
        self.error = error
        self.calls: list[tuple] = []

    async def put(self, bid, seq: int) -> PutResult:
        self.calls.append((bid, seq))
        if self.error is not None:
            raise self.error
        return self._result

    async def ping(self) -> None:
        return None

    async def aclose(self) -> None:
        return None


@pytest.fixture
def buffer_stub_factory():
    """Создаёт заглушку Buffer с заданным результатом или ошибкой put."""

    def factory(
        result: PutResult | None = None,
        error: Exception | None = None,
    ) -> StubBuffer:
        return StubBuffer(result=result, error=error)

    return factory
