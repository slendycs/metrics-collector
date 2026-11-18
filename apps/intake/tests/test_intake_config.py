import allure
import pytest
from pydantic import ValidationError

from intake.config.config import Settings
from models import BufferTypes, LogLevel


def _make_settings(**overrides) -> Settings:
    values = {
        "buffer_type": "REDIS",
        "buffer_capacity": 3,
        "redis_url": "redis://redis.test:6379/0",
        "stats_server_url": "http://stats.test",
        "log_level": "INFO",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore


class TestIntakeConfig:
    @pytest.mark.unit
    @allure.title("Значения буфера и логгера по умолчанию [UNIT]")
    def test_defaults(self):
        with allure.step("Создать настройки без явных значений по умолчанию"):
            settings = _make_settings()

        with allure.step("Проверить тип буфера, адрес статистики и уровень логирования"):
            assert settings.buffer_type is BufferTypes.REDIS
            assert settings.stats_server_url == "http://stats.test"
            assert settings.log_level is LogLevel.INFO

    @pytest.mark.unit
    @allure.title("Параметры uvicorn имеют значения по умолчанию [UNIT]")
    def test_uvicorn_defaults(self):
        with allure.step("Создать настройки без явных параметров uvicorn"):
            settings = _make_settings()

        with allure.step("Проверить хост 0.0.0.0 и порт 8000"):
            assert settings.uvicorn_host == "0.0.0.0"
            assert settings.uvicorn_port == 8000

    @pytest.mark.unit
    @allure.title("Параметры uvicorn читаются из переменных окружения [UNIT]")
    def test_reads_uvicorn_values_from_environment(self, monkeypatch):
        with allure.step("Задать UVICORN_HOST и UVICORN_PORT в окружении"):
            monkeypatch.setenv("UVICORN_HOST", "127.0.0.5")
            monkeypatch.setenv("UVICORN_PORT", "8124")

        with allure.step("Создать настройки без .env файла"):
            settings = Settings(_env_file=None)  # type: ignore

        with allure.step("Проверить хост и порт из окружения"):
            assert settings.uvicorn_host == "127.0.0.5"
            assert settings.uvicorn_port == 8124

    @pytest.mark.unit
    @allure.title("Настройки принимают граничный порт uvicorn {port} [UNIT]")
    @pytest.mark.parametrize(
        "port",
        [
            pytest.param(1, id="min"),
            pytest.param(65535, id="max"),
        ],
    )
    def test_accepts_boundary_uvicorn_port(self, port):
        with allure.step(f"Создать настройки с портом {port}"):
            settings = _make_settings(uvicorn_port=port)

        with allure.step("Проверить сохранённый порт"):
            assert settings.uvicorn_port == port

    @pytest.mark.unit
    @allure.title("Настройки отклоняют недопустимый порт uvicorn {port} [UNIT]")
    @pytest.mark.parametrize(
        "port",
        [
            pytest.param(0, id="zero"),
            pytest.param(-1, id="negative"),
            pytest.param(65536, id="too-large"),
        ],
    )
    def test_rejects_invalid_uvicorn_port(self, port):
        with allure.step(f"Попытаться создать настройки с портом {port}"):
            with pytest.raises(ValidationError):
                _make_settings(uvicorn_port=port)

    @pytest.mark.unit
    @allure.title("Настройки принимают корректную ёмкость буфера [UNIT]")
    def test_accepts_valid_capacity(self):
        with allure.step("Создать настройки с ёмкостью 10"):
            settings = _make_settings(buffer_capacity=10)

        with allure.step("Проверить сохранённую ёмкость"):
            assert settings.buffer_capacity == 10

    @pytest.mark.unit
    @allure.title("Настройки отклоняют ёмкость буфера {capacity} [UNIT]")
    @pytest.mark.parametrize(
        "capacity",
        [
            pytest.param(0, id="zero"),
            pytest.param(-5, id="negative"),
        ],
    )
    def test_rejects_non_positive_capacity(self, capacity):
        with allure.step(f"Попытаться создать настройки с ёмкостью {capacity}"):
            with pytest.raises(ValidationError):
                _make_settings(buffer_capacity=capacity)

    @pytest.mark.unit
    @allure.title("Настройки требуют ёмкость буфера [UNIT]")
    def test_requires_capacity(self, monkeypatch):
        with allure.step("Убрать BUFFER_CAPACITY из окружения"):
            monkeypatch.delenv("BUFFER_CAPACITY", raising=False)

        with allure.step("Создать настройки без ёмкости"):
            with pytest.raises(ValidationError):
                Settings(  # type: ignore
                    _env_file=None,
                    redis_url="redis://redis.test:6379/0",
                    stats_server_url="http://stats.test",
                )

    @pytest.mark.unit
    @allure.title("Настройки требуют адрес сервера статистики [UNIT]")
    def test_requires_stats_server_url(self, monkeypatch):
        with allure.step("Убрать STATS_SERVER_URL из окружения"):
            monkeypatch.delenv("STATS_SERVER_URL", raising=False)

        with allure.step("Создать настройки без адреса статистики"):
            with pytest.raises(ValidationError, match="stats_server_url"):
                Settings(  # type: ignore
                    _env_file=None,
                    buffer_capacity=3,
                    redis_url="redis://redis.test:6379/0",
                )

    @pytest.mark.unit
    @allure.title("Redis-буфер требует URL подключения [UNIT]")
    def test_redis_buffer_requires_url(self, monkeypatch):
        with allure.step("Убрать REDIS_URL из окружения"):
            monkeypatch.delenv("REDIS_URL", raising=False)

        with allure.step("Создать настройки Redis-буфера без URL"):
            with pytest.raises(ValueError, match="no connection url"):
                Settings(  # type: ignore
                    _env_file=None,
                    buffer_type="REDIS",
                    buffer_capacity=3,
                    stats_server_url="http://stats.test",
                )

    @pytest.mark.unit
    @allure.title("Настройки отклоняют неизвестный тип буфера [UNIT]")
    def test_rejects_unknown_buffer_type(self):
        with allure.step("Передать buffer_type=memcached"):
            with pytest.raises(ValidationError):
                _make_settings(buffer_type="memcached")

    @pytest.mark.unit
    @allure.title("Настройки читаются из переменных окружения [UNIT]")
    def test_reads_values_from_environment(self, monkeypatch):
        with allure.step("Задать значения через переменные окружения"):
            monkeypatch.setenv("BUFFER_TYPE", "REDIS")
            monkeypatch.setenv("BUFFER_CAPACITY", "8")
            monkeypatch.setenv("REDIS_URL", "redis://env.test:6379/2")
            monkeypatch.setenv("STATS_SERVER_URL", "http://stats.env.test")
            monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        with allure.step("Создать настройки без .env файла"):
            settings = Settings(_env_file=None)  # type: ignore

        with allure.step("Проверить значения из окружения"):
            assert settings.buffer_type is BufferTypes.REDIS
            assert settings.buffer_capacity == 8
            assert settings.redis_url == "redis://env.test:6379/2"
            assert settings.stats_server_url == "http://stats.env.test"
            assert settings.log_level is LogLevel.DEBUG

    @pytest.mark.integration
    @allure.title("Настройки читаются из реального .env файла [INTEGRATION]")
    def test_reads_settings_from_real_env_file(self, monkeypatch, tmp_path):
        with allure.step("Очистить одноимённые переменные окружения"):
            for name in (
                "BUFFER_TYPE",
                "BUFFER_CAPACITY",
                "REDIS_URL",
                "STATS_SERVER_URL",
                "LOG_LEVEL",
            ):
                monkeypatch.delenv(name, raising=False)

        with allure.step("Записать временный .env файл"):
            env_file = tmp_path / ".env"
            env_file.write_text(
                "BUFFER_TYPE=REDIS\n"
                "BUFFER_CAPACITY=5\n"
                "REDIS_URL=redis://file.test:6379/1\n"
                "STATS_SERVER_URL=http://stats.file.test\n"
                "LOG_LEVEL=WARNING\n",
                encoding="utf-8",
            )

        with allure.step("Прочитать настройки из .env файла"):
            settings = Settings(_env_file=env_file)  # type: ignore

        with allure.step("Проверить значения из файла"):
            assert settings.buffer_type is BufferTypes.REDIS
            assert settings.buffer_capacity == 5
            assert settings.redis_url == "redis://file.test:6379/1"
            assert settings.stats_server_url == "http://stats.file.test"
            assert settings.log_level is LogLevel.WARNING
