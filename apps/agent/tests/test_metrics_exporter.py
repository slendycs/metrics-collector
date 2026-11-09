from datetime import datetime
from unittest.mock import MagicMock, patch

import allure
import pytest

from models import ServerStats
from models.enums import ServerTypes


def _disk_counters(read: int, write: int) -> MagicMock:
    counters = MagicMock()
    counters.read_bytes = read
    counters.write_bytes = write
    return counters


class TestMetricsExporter:
    @pytest.mark.unit
    @allure.title("Чтение счётчиков диска возвращает нули при их отсутствии [UNIT]")
    def test_read_disk_bytes_returns_zero_when_psutil_has_no_counters(self, exporter):
        with allure.step("Смоделировать отсутствие счётчиков в psutil"):
            with patch(
                "exporter.metrics_exporter.psutil.disk_io_counters", return_value=None
            ):
                with allure.step("Прочитать счётчики диска"):
                    result = exporter._read_disk_bytes()

        with allure.step("Проверить нулевые значения"):
            assert result == (0, 0)

    @pytest.mark.unit
    @allure.title("Чтение счётчиков диска возвращает байты чтения и записи [UNIT]")
    def test_read_disk_bytes_returns_counters(self, exporter):
        counters = _disk_counters(read=2048, write=4096)

        with allure.step("Смоделировать счётчики psutil"):
            with patch(
                "exporter.metrics_exporter.psutil.disk_io_counters",
                return_value=counters,
            ) as disk_io_counters:
                with allure.step("Прочитать счётчики диска"):
                    result = exporter._read_disk_bytes()

        with allure.step("Проверить байты и вызов psutil"):
            assert result == (2048, 4096)
            disk_io_counters.assert_called_once_with(perdisk=False)

    @pytest.mark.unit
    @allure.title("collect собирает ServerStats и считает скорость диска [UNIT]")
    def test_collect_builds_server_stats_from_psutil(self, exporter):
        with allure.step("Подготовить параметры экспортёра и счётчики диска"):
            exporter._server_name = "node-7"
            exporter._server_type = ServerTypes.PRODUCTION
            exporter._interval = 0.5
            before = _disk_counters(read=0, write=0)
            after = _disk_counters(read=768_000, write=256_000)

        with allure.step("Собрать метрики с моками psutil"):
            with (
                patch(
                    "exporter.metrics_exporter.psutil.disk_io_counters",
                    side_effect=[before, after],
                ),
                patch(
                    "exporter.metrics_exporter.psutil.cpu_percent", return_value=55.5
                ) as cpu_percent,
                patch(
                    "exporter.metrics_exporter.psutil.virtual_memory",
                    return_value=MagicMock(percent=61.2),
                ),
                patch(
                    "exporter.metrics_exporter.psutil.getloadavg",
                    return_value=(1.1, 2.2, 3.3),
                ),
                patch(
                    "exporter.metrics_exporter.time.monotonic",
                    side_effect=[10.0, 11.0],
                ),
            ):
                result = exporter.collect()

        with allure.step("Проверить поля ServerStats"):
            assert isinstance(result, ServerStats)
            assert result.server_name == "node-7"
            assert result.server_type is ServerTypes.PRODUCTION
            assert result.metrics.cpu_load == 55.5
            assert result.metrics.ram_load == 61.2
            assert result.metrics.disk_read == 750
            assert result.metrics.disk_write == 250
            assert result.metrics.load_average == [1.1, 2.2, 3.3]
            assert isinstance(result.metrics.timestamp, datetime)

        with allure.step("Проверить вызов psutil с интервалом экспортёра"):
            cpu_percent.assert_called_once_with(interval=0.5)

    @pytest.mark.unit
    @allure.title("collect ограничивает отрицательную скорость диска нулём [UNIT]")
    def test_collect_clamps_negative_disk_delta_to_zero(self, exporter):
        with allure.step("Подготовить уменьшившиеся счётчики диска"):
            exporter._interval = 0.1
            exporter._server_name = "node-7"
            exporter._server_type = ServerTypes.TEST
            before = _disk_counters(read=10_000, write=10_000)
            after = _disk_counters(read=5_000, write=4_000)

        with allure.step("Собрать метрики с моками psutil"):
            with (
                patch(
                    "exporter.metrics_exporter.psutil.disk_io_counters",
                    side_effect=[before, after],
                ),
                patch(
                    "exporter.metrics_exporter.psutil.cpu_percent", return_value=1.0
                ),
                patch(
                    "exporter.metrics_exporter.psutil.virtual_memory",
                    return_value=MagicMock(percent=2.0),
                ),
                patch(
                    "exporter.metrics_exporter.psutil.getloadavg",
                    return_value=(0.0, 0.0, 0.0),
                ),
                patch(
                    "exporter.metrics_exporter.time.monotonic",
                    side_effect=[0.0, 1.0],
                ),
            ):
                result = exporter.collect()

        with allure.step("Проверить, что скорости чтения и записи равны нулю"):
            assert result.metrics.disk_read == 0
            assert result.metrics.disk_write == 0

    @pytest.mark.integration
    @allure.title("collect получает реальные метрики через psutil [INTEGRATION]")
    def test_collect_uses_real_psutil(self, exporter):
        with allure.step("Уменьшить интервал измерения CPU"):
            exporter._interval = 0.05

        with allure.step("Собрать метрики через реальный psutil"):
            result = exporter.collect()

        with allure.step("Проверить типы и допустимые диапазоны метрик"):
            assert isinstance(result, ServerStats)
            assert isinstance(result.server_type, ServerTypes)
            assert 0.0 <= result.metrics.cpu_load <= 100.0
            assert 0.0 <= result.metrics.ram_load <= 100.0
            assert result.metrics.disk_read >= 0
            assert result.metrics.disk_write >= 0
            assert len(result.metrics.load_average) == 3
            assert isinstance(result.metrics.timestamp, datetime)
