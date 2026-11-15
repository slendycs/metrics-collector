from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import allure
import pytest

from buffer import RedisBuffer
from intake.config.dependencies import create_buffer, get_buffer
from models import BufferTypes


class TestIntakeDependencies:
    @pytest.mark.unit
    @allure.title("create_buffer собирает RedisBuffer из настроек [UNIT]")
    def test_creates_redis_buffer(self):
        with allure.step("Подготовить настройки Redis-буфера"):
            settings = SimpleNamespace(
                buffer_type=BufferTypes.REDIS,
                buffer_capacity=7,
                redis_url="redis://redis.test:6379/0",
            )
            redis_client = MagicMock()

        with allure.step("Создать буфер с подменёнными настройками и Redis"):
            with (
                patch("intake.config.dependencies.settings", settings),
                patch(
                    "intake.config.dependencies.aioredis.from_url",
                    return_value=redis_client,
                ) as from_url,
            ):
                buffer = create_buffer()

        with allure.step("Проверить тип буфера и подключение к Redis"):
            assert isinstance(buffer, RedisBuffer)
            assert buffer._capacity == 7
            from_url.assert_called_once_with(
                "redis://redis.test:6379/0",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                health_check_interval=30,
            )

        with allure.step("Проверить регистрацию Lua-скриптов на клиенте"):
            assert redis_client.register_script.call_count == 3

    @pytest.mark.unit
    @allure.title("create_buffer требует redis_url для Redis-буфера [UNIT]")
    def test_requires_redis_url(self):
        with allure.step("Подготовить настройки без redis_url"):
            settings = SimpleNamespace(
                buffer_type=BufferTypes.REDIS,
                buffer_capacity=3,
                redis_url=None,
            )

        with allure.step("Попытаться создать буфер"):
            with (
                patch("intake.config.dependencies.settings", settings),
                pytest.raises(ValueError, match="redis_url is required"),
            ):
                create_buffer()

    @pytest.mark.unit
    @allure.title("create_buffer отклоняет неподдерживаемый тип буфера [UNIT]")
    def test_rejects_unsupported_buffer_type(self):
        with allure.step("Подготовить настройки с неизвестным типом буфера"):
            settings = SimpleNamespace(
                buffer_type="memcached",
                buffer_capacity=3,
                redis_url="redis://redis.test:6379/0",
            )

        with allure.step("Попытаться создать буфер"):
            with (
                patch("intake.config.dependencies.settings", settings),
                pytest.raises(ValueError, match="Unsupported buffer type"),
            ):
                create_buffer()

    @pytest.mark.unit
    @allure.title("get_buffer отдаёт буфер из состояния приложения [UNIT]")
    def test_returns_buffer_from_app_state(self):
        with allure.step("Подготовить приложение с буфером в state"):
            buffer = MagicMock()
            request = SimpleNamespace(
                app=SimpleNamespace(state=SimpleNamespace(buffer=buffer))
            )

        with allure.step("Получить буфер через зависимость"):
            result = get_buffer(request)

        with allure.step("Проверить, что вернулся буфер приложения"):
            assert result is buffer
