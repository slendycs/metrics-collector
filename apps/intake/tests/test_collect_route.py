from datetime import datetime
from unittest.mock import patch

import allure
import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from buffer import BufferConnectionError, BufferException, BufferTimeoutError
from intake.config import get_buffer
from intake.main import app
from intake.routes.collect import collect_metrics
from models import PutResult, PutResultDTO, ServerTypes
from models.metrics import MetricsDTO


def _make_validation_error() -> ValidationError:
    """Собирает настоящий ValidationError, как при разборе сломанного пакета."""
    try:
        MetricsDTO.model_validate({"cpu_load": "not-a-number"})
    except ValidationError as err:
        return err
    raise AssertionError("MetricsDTO должен был не пройти валидацию")


async def _post_collect(payload: dict, buffer) -> httpx.Response:
    """Шлёт POST /collect в ASGI-приложение с подменённым буфером."""
    app.dependency_overrides[get_buffer] = lambda: buffer
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://intake.test"
        ) as client:
            return await client.post("/collect", json=payload)
    finally:
        app.dependency_overrides.pop(get_buffer, None)


class TestCollectRoute:
    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error_class", "expected_status", "log_method"),
        [
            pytest.param(BufferTimeoutError, 504, "error", id="timeout"),
            pytest.param(BufferConnectionError, 502, "critical", id="connection"),
            pytest.param(BufferException, 500, "error", id="generic"),
        ],
    )
    @allure.title(
        "{error_class.__name__} из буфера превращается в HTTP {expected_status} [UNIT]"
    )
    async def test_maps_buffer_error_to_http_status(
        self,
        buffer_stub_factory,
        server_stats_dto,
        error_class,
        expected_status,
        log_method,
    ):
        with allure.step("Подготовить буфер, падающий доменной ошибкой"):
            error = error_class("redis failure")
            buffer = buffer_stub_factory(error=error)

        with allure.step("Вызвать обработчик collect_metrics"):
            with patch("intake.routes.collect.logger") as logger:
                with pytest.raises(HTTPException) as exc_info:
                    await collect_metrics(server_stats_dto, buffer=buffer)

        with allure.step("Проверить код ответа и исходную причину"):
            assert exc_info.value.status_code == expected_status
            assert exc_info.value.__cause__ is error

        with allure.step(f"Проверить запись в лог через logger.{log_method}"):
            getattr(logger, log_method).assert_called_once_with(error)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("Ошибка сериализации в буфере превращается в HTTP 500 [UNIT]")
    async def test_maps_validation_error_to_internal_error(
        self, buffer_stub_factory, server_stats_dto
    ):
        with allure.step("Подготовить буфер, падающий ValidationError"):
            error = _make_validation_error()
            buffer = buffer_stub_factory(error=error)

        with allure.step("Вызвать обработчик collect_metrics"):
            with patch("intake.routes.collect.logger") as logger:
                with pytest.raises(HTTPException) as exc_info:
                    await collect_metrics(server_stats_dto, buffer=buffer)

        with allure.step("Проверить код 500 и исходную причину"):
            assert exc_info.value.status_code == 500
            assert exc_info.value.__cause__ is error

        with allure.step("Проверить запись ошибки в лог"):
            logger.error.assert_called_once_with(error)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("Успешный collect собирает Bid из DTO и время поступления [UNIT]")
    async def test_builds_bid_from_stats(
        self, buffer_stub_factory, server_stats_dto, stats_client_stub
    ):
        with allure.step("Зафиксировать время поступления заявки"):
            fixed_now = datetime(2026, 3, 1, 10, 30)

        with allure.step("Подготовить буфер с успешным результатом"):
            expected = PutResult(
                accepted=True,
                bid_id=42,
                seq=7,
                source_name="agent-1",
                source_type=ServerTypes.TEST,
                slot=2,
            )
            buffer = buffer_stub_factory(result=expected)

        with allure.step("Вызвать обработчик с подменённым временем и статистикой"):
            with patch("intake.routes.collect.datetime") as datetime_mock:
                with patch(
                    "intake.routes.collect.StatsClient",
                    return_value=stats_client_stub,
                ):
                    datetime_mock.now.return_value = fixed_now
                    response = await collect_metrics(server_stats_dto, buffer=buffer)

        with allure.step("Проверить, что вернулся результат буфера"):
            assert response is expected
            assert PutResultDTO.model_validate(response) == PutResultDTO(
                accepted=True,
                bid_id=42,
                seq=7,
                source_name="agent-1",
                source_type=ServerTypes.TEST,
                slot=2,
            )

        with allure.step("Проверить отправку результата в статистику"):
            assert stats_client_stub.calls == [expected]

        with allure.step("Проверить переданную в буфер заявку и seq"):
            bid, seq = buffer.calls[0]
            assert seq == server_stats_dto.seq == 7
            assert bid.source_name == server_stats_dto.server_name == "agent-1"
            assert bid.source_type is ServerTypes.TEST
            assert bid.time_in == fixed_now
            assert bid.stats == server_stats_dto.metrics.to_obj()
            assert bid.id is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title("POST /collect возвращает 201 и PutResultDTO [INTEGRATION]")
    async def test_returns_created_result(
        self, buffer_stub_factory, server_stats_payload, stats_client_stub
    ):
        with allure.step("Подготовить буфер-заглушку с результатом"):
            expected = PutResult(
                accepted=True,
                bid_id=42,
                seq=7,
                source_name="agent-1",
                source_type=ServerTypes.TEST,
                slot=2,
            )
            buffer = buffer_stub_factory(result=expected)

        with allure.step("Отправить POST /collect через ASGI-приложение"):
            with patch("intake.routes.collect.logger"):
                with patch(
                    "intake.routes.collect.StatsClient",
                    return_value=stats_client_stub,
                ):
                    response = await _post_collect(server_stats_payload, buffer)

        with allure.step("Проверить код ответа и тело PutResultDTO"):
            assert response.status_code == 201
            assert response.json() == {
                "accepted": True,
                "bid_id": 42,
                "seq": 7,
                "source_name": "agent-1",
                "source_type": "test",
                "slot": 2,
            }

        with allure.step("Проверить, что маршрут передал заявку в буфер"):
            bid, seq = buffer.calls[0]
            assert (bid.source_name, seq) == ("agent-1", 7)

        with allure.step("Проверить отправку результата в статистику"):
            assert stats_client_stub.calls == [expected]

    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error_class", "expected_status", "expected_detail"),
        [
            pytest.param(BufferTimeoutError, 504, "Gateway Timeout", id="timeout"),
            pytest.param(BufferConnectionError, 502, "Bad Gateway", id="connection"),
            pytest.param(
                BufferException, 500, "Internal Server Error", id="generic"
            ),
        ],
    )
    @allure.title(
        "POST /collect отдаёт HTTP {expected_status} при ошибке "
        "{error_class.__name__} [INTEGRATION]"
    )
    async def test_returns_error_status(
        self,
        buffer_stub_factory,
        server_stats_payload,
        error_class,
        expected_status,
        expected_detail,
    ):
        with allure.step("Подготовить буфер, падающий доменной ошибкой"):
            buffer = buffer_stub_factory(error=error_class("redis failure"))

        with allure.step("Отправить POST /collect через ASGI-приложение"):
            with patch("intake.routes.collect.logger"):
                response = await _post_collect(server_stats_payload, buffer)

        with allure.step("Проверить код ответа и стандартный detail"):
            assert response.status_code == expected_status
            assert response.json() == {"detail": expected_detail}

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title(
        "POST /collect отдаёт HTTP 500 при ошибке сериализации [INTEGRATION]"
    )
    async def test_returns_internal_error_on_validation_failure(
        self, buffer_stub_factory, server_stats_payload
    ):
        with allure.step("Подготовить буфер, падающий ValidationError"):
            buffer = buffer_stub_factory(error=_make_validation_error())

        with allure.step("Отправить POST /collect через ASGI-приложение"):
            with patch("intake.routes.collect.logger"):
                response = await _post_collect(server_stats_payload, buffer)

        with allure.step("Проверить код 500 и стандартный detail"):
            assert response.status_code == 500
            assert response.json() == {"detail": "Internal Server Error"}

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title(
        "Недоступный сервер статистики не мешает вернуть результат буфера [UNIT]"
    )
    async def test_returns_result_when_stats_server_unavailable(
        self, buffer_stub_factory, server_stats_dto, stats_client_stub_factory
    ):
        with allure.step("Подготовить буфер и статистику, падающую ConnectError"):
            expected = PutResult(
                accepted=True,
                bid_id=42,
                seq=7,
                source_name="agent-1",
                source_type=ServerTypes.TEST,
                slot=2,
            )
            buffer = buffer_stub_factory(result=expected)
            error = httpx.ConnectError("stats server is down")
            stats_client = stats_client_stub_factory(error=error)

        with allure.step("Вызвать обработчик collect_metrics"):
            with patch(
                "intake.routes.collect.StatsClient", return_value=stats_client
            ):
                with patch("intake.routes.collect.logger") as logger:
                    response = await collect_metrics(server_stats_dto, buffer=buffer)

        with allure.step("Проверить, что результат буфера всё равно возвращён"):
            assert response is expected
            assert stats_client.calls == [expected]

        with allure.step("Проверить запись ошибки статистики в лог"):
            logger.warning.assert_called_once()
            message = str(logger.warning.call_args.args[0])
            assert "Failed to send metrics" in message
            assert "stats server is down" in message

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title(
        "POST /collect отдаёт 201, когда сервер статистики недоступен [INTEGRATION]"
    )
    async def test_returns_created_when_stats_server_unavailable(
        self, buffer_stub_factory, server_stats_payload, stats_client_stub_factory
    ):
        with allure.step("Подготовить буфер и статистику, падающую ConnectError"):
            expected = PutResult(
                accepted=True,
                bid_id=42,
                seq=7,
                source_name="agent-1",
                source_type=ServerTypes.TEST,
                slot=2,
            )
            buffer = buffer_stub_factory(result=expected)
            stats_client = stats_client_stub_factory(
                error=httpx.ConnectError("stats server is down")
            )

        with allure.step("Отправить POST /collect через ASGI-приложение"):
            with patch(
                "intake.routes.collect.StatsClient", return_value=stats_client
            ):
                with patch("intake.routes.collect.logger") as logger:
                    response = await _post_collect(server_stats_payload, buffer)

        with allure.step("Проверить код 201 и тело PutResultDTO"):
            assert response.status_code == 201
            assert response.json() == {
                "accepted": True,
                "bid_id": 42,
                "seq": 7,
                "source_name": "agent-1",
                "source_type": "test",
                "slot": 2,
            }

        with allure.step("Проверить запись ошибки статистики в лог"):
            logger.warning.assert_called_once()

        with allure.step("Проверить, что статистике отправлен результат буфера"):
            assert stats_client.calls == [expected]
