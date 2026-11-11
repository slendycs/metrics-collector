from unittest.mock import MagicMock, patch

import allure
import psutil
import pytest
from pydantic import ValidationError
from requests import HTTPError

from client import Client
from exporter import MetricsExporter
from manager import PoolingManager


class _StopPooling(Exception):
    """Breaks the infinite pooling loop after a single iteration."""


def _validation_error() -> ValidationError:
    return ValidationError.from_exception_data(
        "MetricsDTO",
        [{"type": "missing", "loc": ("cpu_load",), "input": {}}],
    )


def _run_single_iteration(
    manager: PoolingManager,
    *,
    collect_result=None,
    collect_effect=None,
    post_effect=None,
    timeout_min: int = 1,
    timeout_max: int = 3,
) -> MagicMock:
    with allure.step("Подготовить моки экспортёра и клиента"):
        manager._exporter = MagicMock()
        manager._client = MagicMock()
        settings = MagicMock(timeout_min=timeout_min, timeout_max=timeout_max)
        if collect_result is not None:
            manager._exporter.collect.return_value = collect_result
        if collect_effect is not None:
            manager._exporter.collect.side_effect = collect_effect
        if post_effect is not None:
            manager._client.post.side_effect = post_effect

    with allure.step("Выполнить одну итерацию цикла опроса"):
        with (
            patch(
                "manager.pooling_manager.get_settings", return_value=settings
            ),
            patch(
                "manager.pooling_manager.sleep", side_effect=_StopPooling
            ) as sleep_mock,
        ):
            with pytest.raises(_StopPooling):
                manager.pooling()

    return sleep_mock


class TestPoolingManager:
    @pytest.mark.unit
    @allure.title("Успешная итерация отправляет метрики и уходит в sleep [UNIT]")
    def test_successful_iteration_sends_metrics_and_sleeps(
        self, pooling_manager, server_stats
    ):
        with allure.step("Перехватить логгер"):
            with patch("manager.pooling_manager.logger") as logger_mock:
                sleep_mock = _run_single_iteration(
                    pooling_manager, collect_result=server_stats
                )

        with allure.step("Проверить сбор и отправку метрик"):
            pooling_manager._exporter.collect.assert_called_once_with()
            pooling_manager._client.post.assert_called_once_with(server_stats)

        with allure.step("Проверить паузу в пределах настроенного диапазона"):
            timeout = sleep_mock.call_args.args[0]
            assert 1 <= timeout <= 3

        with allure.step("Проверить логирование успешной итерации"):
            logger_mock.info.assert_called_once()
            logger_mock.error.assert_not_called()
            logger_mock.critical.assert_not_called()

    @pytest.mark.unit
    @allure.title("HTTPError логируется, а цикл продолжает работу [UNIT]")
    def test_http_error_is_logged_and_loop_continues(
        self, pooling_manager, server_stats
    ):
        with allure.step("Смоделировать HTTPError при отправке"):
            error = HTTPError("500 Server Error")

        with allure.step("Выполнить итерацию с перехватом логгера"):
            with patch("manager.pooling_manager.logger") as logger_mock:
                sleep_mock = _run_single_iteration(
                    pooling_manager,
                    collect_result=server_stats,
                    post_effect=error,
                )

        with allure.step("Проверить запись ошибки в лог"):
            logger_mock.error.assert_called_once()
            assert "500 Server Error" in logger_mock.error.call_args.args[0]
            logger_mock.critical.assert_not_called()

        with allure.step("Проверить, что цикл дошёл до sleep"):
            sleep_mock.assert_called_once()

    @pytest.mark.unit
    @allure.title(
        "Ошибка разбора метрик ({error_name}) логируется, цикл продолжается [UNIT]"
    )
    @pytest.mark.parametrize(
        ("error", "error_name"),
        [
            pytest.param(ValueError("bad value"), "ValueError", id="value-error"),
            pytest.param(TypeError("bad type"), "TypeError", id="type-error"),
            pytest.param(
                _validation_error(), "ValidationError", id="validation-error"
            ),
        ],
    )
    def test_parsing_error_is_logged_and_loop_continues(
        self, pooling_manager, error, error_name
    ):
        with allure.step("Выполнить итерацию с ошибкой сбора метрик"):
            with patch("manager.pooling_manager.logger") as logger_mock:
                sleep_mock = _run_single_iteration(
                    pooling_manager, collect_effect=error
                )

        with allure.step("Проверить запись ошибки разбора в лог"):
            logger_mock.error.assert_called_once()
            logger_mock.critical.assert_not_called()

        with allure.step("Проверить, что отправка не выполнялась, а цикл дошёл до sleep"):
            pooling_manager._client.post.assert_not_called()
            sleep_mock.assert_called_once()

    @pytest.mark.unit
    @allure.title(
        "Системная ошибка ({error_name}) логируется как critical, цикл продолжается "
        "[UNIT]"
    )
    @pytest.mark.parametrize(
        ("error", "error_name"),
        [
            pytest.param(OSError("denied"), "OSError", id="os-error"),
            pytest.param(
                psutil.Error("psutil failed"), "psutil.Error", id="psutil-error"
            ),
        ],
    )
    def test_system_error_is_logged_as_critical_and_loop_continues(
        self, pooling_manager, error, error_name
    ):
        with allure.step("Выполнить итерацию с системной ошибкой"):
            with patch("manager.pooling_manager.logger") as logger_mock:
                sleep_mock = _run_single_iteration(
                    pooling_manager, collect_effect=error
                )

        with allure.step("Проверить critical-запись в лог"):
            logger_mock.critical.assert_called_once()
            assert str(error) in logger_mock.critical.call_args.args[0]
            logger_mock.error.assert_not_called()

        with allure.step("Проверить, что отправка не выполнялась, а цикл дошёл до sleep"):
            pooling_manager._client.post.assert_not_called()
            sleep_mock.assert_called_once()

    @pytest.mark.unit
    @allure.title("Непредвиденное исключение не перехватывается [UNIT]")
    def test_unexpected_error_is_not_swallowed(self, pooling_manager, server_stats):
        with allure.step("Подготовить моки и непредвиденную ошибку"):
            pooling_manager._exporter = MagicMock()
            pooling_manager._client = MagicMock()
            pooling_manager._exporter.collect.return_value = server_stats
            pooling_manager._client.post.side_effect = RuntimeError("boom")

        with allure.step("Перехватить логгер и sleep"):
            with (
                patch("manager.pooling_manager.logger") as logger_mock,
                patch(
                    "manager.pooling_manager.sleep", side_effect=_StopPooling
                ) as sleep_mock,
            ):
                with allure.step("Ожидать проброс RuntimeError"):
                    with pytest.raises(RuntimeError, match="boom"):
                        pooling_manager.pooling()

        with allure.step("Проверить, что ошибка не логировалась и sleep не вызывался"):
            logger_mock.error.assert_not_called()
            logger_mock.critical.assert_not_called()
            sleep_mock.assert_not_called()

    @pytest.mark.unit
    @allure.title("sleep использует настроенный диапазон таймаутов [UNIT]")
    def test_sleep_uses_configured_timeout_range(self, pooling_manager, server_stats):
        with allure.step("Перехватить логгер"):
            with patch("manager.pooling_manager.logger"):
                sleep_mock = _run_single_iteration(
                    pooling_manager,
                    collect_result=server_stats,
                    timeout_min=7,
                    timeout_max=7,
                )

        with allure.step("Проверить аргумент sleep"):
            sleep_mock.assert_called_once_with(7)

    @pytest.mark.integration
    @allure.title(
        "Одна итерация доставляет реальные метрики на реальный HTTP-сервер "
        "[INTEGRATION]"
    )
    def test_pooling_sends_real_metrics_to_real_http_server(
        self, pooling_manager, http_server
    ):
        with allure.step("Подготовить реальные экспортёр и клиент"):
            host, port = http_server.server_address[:2]

            exporter = MetricsExporter()
            exporter._interval = 0.01
            client = Client()

            pooling_manager._exporter = exporter
            pooling_manager._client = client

            client_settings = MagicMock(
                reception_service_url=f"http://{host}:{port}"
            )
            manager_settings = MagicMock(timeout_min=0, timeout_max=0)

        with allure.step("Выполнить одну итерацию цикла"):
            with (
                patch(
                    "client.metrics_send_client.get_settings",
                    return_value=client_settings,
                ),
                patch(
                    "manager.pooling_manager.get_settings",
                    return_value=manager_settings,
                ),
                patch("manager.pooling_manager.sleep", side_effect=_StopPooling),
            ):
                with pytest.raises(_StopPooling):
                    pooling_manager.pooling()

        with allure.step("Проверить запрос, полученный реальным сервером"):
            assert len(http_server.requests) == 1
            received = http_server.requests[0]
            assert received["path"] == "/collect"

        with allure.step("Проверить структуру и диапазоны реальных метрик"):
            payload = received["json"]
            assert payload["server_name"]
            assert payload["server_type"] in {"production", "staging", "test"}
            assert payload["seq"] == 1
            assert set(payload["metrics"]) == {
                "cpu_load",
                "ram_load",
                "disk_read",
                "disk_write",
                "load_average",
                "timestamp",
            }
            assert 0.0 <= payload["metrics"]["cpu_load"] <= 100.0
            assert 0.0 <= payload["metrics"]["ram_load"] <= 100.0
