from datetime import datetime

import allure
import pytest
from pydantic import ValidationError

from models import Metrics, ServerStats, ServerStatsDTO
from models.enums import LogLevel, ServerTypes
from models.metrics import MetricsDTO


class TestEnums:
    @pytest.mark.unit
    @allure.title("Справочник ServerTypes содержит production, staging и test [UNIT]")
    def test_server_types_values(self):
        with allure.step("Сравнить значения элементов ServerTypes"):
            assert [item.value for item in ServerTypes] == [
                "production",
                "staging",
                "test",
            ]

    @pytest.mark.unit
    @allure.title("Справочник LogLevel содержит стандартные уровни логирования [UNIT]")
    def test_log_level_values(self):
        with allure.step("Сравнить значения элементов LogLevel"):
            assert [item.value for item in LogLevel] == [
                "DEBUG",
                "INFO",
                "WARNING",
                "ERROR",
                "CRITICAL",
            ]

    @pytest.mark.unit
    @allure.title("ServerTypes ведёт себя как строковое значение [UNIT]")
    def test_server_type_compares_with_string(self):
        with allure.step("Сравнить ServerType со строкой"):
            assert ServerTypes.PRODUCTION == "production"

        with allure.step("Привести ServerType к строке"):
            assert str(ServerTypes.TEST) == "test"


class TestMetricsModels:
    @pytest.mark.unit
    @allure.title("Metrics сохраняет переданные поля [UNIT]")
    def test_metrics_dataclass_keeps_fields(self, metrics):
        with allure.step("Проверить поля Metrics"):
            assert metrics.cpu_load == 12.5
            assert metrics.ram_load == 43.2
            assert metrics.disk_read == 1024
            assert metrics.disk_write == 512
            assert metrics.load_average == [0.1, 0.2, 0.3]
            assert metrics.timestamp == datetime(2026, 1, 1, 12, 0, 0)

    @pytest.mark.unit
    @allure.title("MetricsDTO собирается из Metrics через from_attributes [UNIT]")
    def test_metrics_dto_is_built_from_dataclass(self, metrics):
        with allure.step("Преобразовать Metrics в MetricsDTO"):
            dto = MetricsDTO.model_validate(metrics)

        with allure.step("Сравнить поля DTO и исходной модели"):
            assert dto.cpu_load == metrics.cpu_load
            assert dto.ram_load == metrics.ram_load
            assert dto.disk_read == metrics.disk_read
            assert dto.disk_write == metrics.disk_write
            assert dto.load_average == metrics.load_average
            assert dto.timestamp == metrics.timestamp

    @pytest.mark.unit
    @allure.title("MetricsDTO отклоняет неполный payload [UNIT]")
    def test_metrics_dto_rejects_incomplete_payload(self):
        with allure.step("Провалидировать payload без обязательных полей"):
            with pytest.raises(ValidationError):
                MetricsDTO.model_validate({"cpu_load": 1.0})

    @pytest.mark.unit
    @allure.title("MetricsDTO неизменяем после создания [UNIT]")
    def test_metrics_dto_is_frozen(self, metrics):
        with allure.step("Преобразовать Metrics в MetricsDTO"):
            dto = MetricsDTO.model_validate(metrics)

        with allure.step("Попытаться изменить поле DTO"):
            with pytest.raises(ValidationError):
                dto.cpu_load = 0.0

    @pytest.mark.unit
    @allure.title("MetricsDTO сериализует timestamp в JSON-строку [UNIT]")
    def test_metrics_dto_serializes_timestamp_to_json(self, metrics):
        with allure.step("Сериализовать MetricsDTO в JSON-совместимый dict"):
            payload = MetricsDTO.model_validate(metrics).model_dump(mode="json")

        with allure.step("Проверить формат timestamp и списка load_average"):
            assert payload["timestamp"] == "2026-01-01T12:00:00"
            assert payload["load_average"] == [0.1, 0.2, 0.3]

    @pytest.mark.unit
    @allure.title("ServerStatsDTO вкладывает метрики как MetricsDTO [UNIT]")
    def test_server_stats_dto_nests_metrics(self, server_stats):
        with allure.step("Преобразовать ServerStats в ServerStatsDTO"):
            dto = ServerStatsDTO.model_validate(server_stats)

        with allure.step("Проверить вложенный MetricsDTO"):
            assert dto.server_name == "agent-1"
            assert dto.server_type is ServerTypes.TEST
            assert isinstance(dto.metrics, MetricsDTO)
            assert dto.metrics.disk_read == server_stats.metrics.disk_read

    @pytest.mark.unit
    @allure.title("ServerStats сохраняет метрики и тип сервера [UNIT]")
    def test_server_stats_dataclass_keeps_fields(self, server_stats):
        with allure.step("Проверить поля ServerStats"):
            assert isinstance(server_stats.metrics, Metrics)
            assert server_stats.server_name == "agent-1"
            assert server_stats.server_type is ServerTypes.TEST
