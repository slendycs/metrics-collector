from unittest.mock import AsyncMock, MagicMock, patch

import allure
import pytest
from fastapi import FastAPI

from intake.main import app, lifespan


class TestApp:
    @pytest.mark.unit
    @allure.title("Приложение регистрирует маршруты collect и health [UNIT]")
    def test_app_registers_routers(self):
        with allure.step("Собрать пути из OpenAPI-схемы приложения"):
            paths = set(app.openapi()["paths"])

        with allure.step("Проверить наличие маршрутов intake и service"):
            assert "/collect" in paths
            assert "/health" in paths

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("Приложение запускает lifespan для создания буфера [UNIT]")
    async def test_app_uses_lifespan(self):
        with allure.step("Подготовить мок буфера"):
            buffer = MagicMock()
            buffer.ping = AsyncMock()
            buffer.aclose = AsyncMock()

        with allure.step("Запустить lifespan приложения"):
            with patch("intake.main.create_buffer", return_value=buffer) as create:
                async with app.router.lifespan_context(app):
                    with allure.step("Проверить, что буфер создан и доступен"):
                        create.assert_called_once_with()
                        assert app.state.buffer is buffer

        with allure.step("Проверить освобождение ресурсов"):
            buffer.aclose.assert_awaited_once_with()


class TestLifespan:
    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("lifespan создаёт буфер, проверяет его и закрывает [UNIT]")
    async def test_lifespan_manages_buffer(self):
        with allure.step("Подготовить приложение и мок буфера"):
            test_app = FastAPI()
            buffer = MagicMock()
            buffer.ping = AsyncMock()
            buffer.aclose = AsyncMock()

        with allure.step("Открыть и закрыть lifespan"):
            with patch("intake.main.create_buffer", return_value=buffer) as create:
                async with lifespan(test_app):
                    with allure.step("Проверить буфер внутри lifespan"):
                        assert test_app.state.buffer is buffer
                        create.assert_called_once_with()
                        buffer.ping.assert_awaited_once_with()
                        buffer.aclose.assert_not_awaited()

        with allure.step("Проверить освобождение ресурсов после выхода"):
            buffer.aclose.assert_awaited_once_with()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("lifespan закрывает буфер при исключении [UNIT]")
    async def test_lifespan_closes_buffer_on_error(self):
        with allure.step("Подготовить приложение и мок буфера"):
            test_app = FastAPI()
            buffer = MagicMock()
            buffer.ping = AsyncMock()
            buffer.aclose = AsyncMock()

        with allure.step("Вызвать lifespan с исключением внутри"):
            with patch("intake.main.create_buffer", return_value=buffer):
                with pytest.raises(RuntimeError, match="boom"):
                    async with lifespan(test_app):
                        raise RuntimeError("boom")

        with allure.step("Проверить закрытие буфера"):
            buffer.aclose.assert_awaited_once_with()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("lifespan пробрасывает ошибку ping и не закрывает буфер [UNIT]")
    async def test_lifespan_propagates_ping_error(self):
        with allure.step("Подготовить буфер с ошибкой ping"):
            test_app = FastAPI()
            buffer = MagicMock()
            buffer.ping = AsyncMock(side_effect=RuntimeError("redis down"))
            buffer.aclose = AsyncMock()

        with allure.step("Открыть lifespan и ожидать ошибку"):
            with patch("intake.main.create_buffer", return_value=buffer):
                with pytest.raises(RuntimeError, match="redis down"):
                    async with lifespan(test_app):
                        pass

        with allure.step("Проверить, что буфер в state не установлен"):
            assert not hasattr(test_app.state, "buffer")

        with allure.step("Проверить, что aclose не вызывался"):
            buffer.aclose.assert_not_awaited()
