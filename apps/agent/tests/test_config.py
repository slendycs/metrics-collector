import allure
import pytest
from pydantic import ValidationError

from config import get_settings
from config.config import Settings


def _make_settings(**overrides) -> Settings:
    values = {
        "server_name": "agent-1",
        "server_type": "test",
        "timeout_min": 1,
        "timeout_max": 5,
        "reception_service_url": "http://reception.test",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values) # type: ignore


class TestSettings:
    @pytest.mark.unit
    @allure.title("LogLevel по умолчанию равен INFO [UNIT]")
    def test_defaults_log_level_to_info(self, monkeypatch):
        with allure.step("Убрать LOG_LEVEL из окружения"):
            monkeypatch.delenv("LOG_LEVEL", raising=False)

        with allure.step("Создать настройки без явного LOG_LEVEL"):
            settings = _make_settings()

        with allure.step("Проверить уровень логирования по умолчанию"):
            assert settings.log_level is not None
            assert settings.log_level.value == "INFO"

    @pytest.mark.unit
    @allure.title("Настройки принимают корректный диапазон таймаутов [UNIT]")
    def test_accepts_valid_timeouts(self):
        with allure.step("Создать настройки с timeout_min < timeout_max"):
            settings = _make_settings(timeout_min=2, timeout_max=10)

        with allure.step("Проверить сохранённые таймауты"):
            assert settings.timeout_min == 2
            assert settings.timeout_max == 10

    @pytest.mark.unit
    @allure.title(
        "Настройки отклоняют таймауты min={timeout_min}, max={timeout_max} [UNIT]"
    )
    @pytest.mark.parametrize(
        ("timeout_min", "timeout_max"),
        [
            pytest.param(5, 5, id="equal"),
            pytest.param(10, 5, id="min-greater"),
        ],
    )
    def test_rejects_non_increasing_timeouts(self, timeout_min, timeout_max):
        with allure.step(
            f"Попытаться создать настройки с timeout_min={timeout_min}, "
            f"timeout_max={timeout_max}"
        ):
            with pytest.raises(ValidationError, match="minimum timeout"):
                _make_settings(timeout_min=timeout_min, timeout_max=timeout_max)

    @pytest.mark.unit
    @allure.title("Настройки отклоняют неизвестный тип сервера [UNIT]")
    def test_rejects_unknown_server_type(self):
        with allure.step("Передать server_type=unknown"):
            with pytest.raises(ValidationError):
                _make_settings(server_type="unknown")

    @pytest.mark.unit
    @allure.title("Настройки читаются из переменных окружения [UNIT]")
    def test_reads_values_from_environment(self, monkeypatch):
        with allure.step("Задать значения через переменные окружения"):
            monkeypatch.setenv("SERVER_NAME", "env-agent")
            monkeypatch.setenv("SERVER_TYPE", "production")
            monkeypatch.setenv("TIMEOUT_MIN", "3")
            monkeypatch.setenv("TIMEOUT_MAX", "7")
            monkeypatch.setenv("RECEPTION_SERVICE_URL", "http://env.test")
            monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        with allure.step("Создать настройки без .env файла"):
            settings = Settings(_env_file=None)

        with allure.step("Проверить значения из окружения"):
            assert settings.server_name == "env-agent"
            assert settings.server_type.value == "production"
            assert settings.timeout_min == 3
            assert settings.timeout_max == 7
            assert settings.reception_service_url == "http://env.test"
            assert settings.log_level.value == "DEBUG"

    @pytest.mark.integration
    @allure.title("Настройки читаются из реального .env файла [INTEGRATION]")
    def test_reads_settings_from_real_env_file(self, monkeypatch, tmp_path):
        with allure.step("Очистить одноимённые переменные окружения"):
            for name in (
                "SERVER_NAME",
                "SERVER_TYPE",
                "TIMEOUT_MIN",
                "TIMEOUT_MAX",
                "RECEPTION_SERVICE_URL",
                "LOG_LEVEL",
            ):
                monkeypatch.delenv(name, raising=False)

        with allure.step("Записать временный .env файл"):
            env_file = tmp_path / ".env"
            env_file.write_text(
                "SERVER_NAME=file-agent\n"
                "SERVER_TYPE=staging\n"
                "TIMEOUT_MIN=2\n"
                "TIMEOUT_MAX=9\n"
                "RECEPTION_SERVICE_URL=http://file.test\n"
                "LOG_LEVEL=WARNING\n",
                encoding="utf-8",
            )

        with allure.step("Прочитать настройки из .env файла"):
            settings = Settings(_env_file=env_file)

        with allure.step("Проверить значения из файла"):
            assert settings.server_name == "file-agent"
            assert settings.server_type.value == "staging"
            assert settings.timeout_min == 2
            assert settings.timeout_max == 9
            assert settings.reception_service_url == "http://file.test"
            assert settings.log_level.value == "WARNING"

    @pytest.mark.unit
    @allure.title("get_settings кэширует созданный объект настроек [UNIT]")
    def test_get_settings_is_cached(self):
        with allure.step("Сбросить кэш настроек"):
            get_settings.cache_clear()

        try:
            with allure.step("Получить настройки дважды"):
                first = get_settings()
                second = get_settings()

            with allure.step("Убедиться, что вернулся один и тот же объект"):
                assert first is second
        finally:
            get_settings.cache_clear()
