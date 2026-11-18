import allure
import httpx
import pytest
from fastapi import HTTPException

from buffer import BufferException
from intake.main import app
from intake.routes.service import health


async def _get_health(buffer) -> httpx.Response:
    """Шлёт GET /health в ASGI-приложение с буфером в состоянии приложения."""
    app.state.buffer = buffer
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://intake.test"
        ) as client:
            return await client.get("/health")
    finally:
        del app.state.buffer


class TestHealthRoute:
    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("health возвращает 200 при доступном буфере [UNIT]")
    async def test_health_returns_200(self, buffer_stub_factory):
        with allure.step("Подготовить доступный буфер"):
            buffer = buffer_stub_factory()

        with allure.step("Вызвать обработчик health с буфером"):
            result = await health(buffer=buffer)

        with allure.step("Проверить код ответа"):
            assert result == 200

    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("health превращает ошибку ping в HTTP 503 [UNIT]")
    async def test_health_maps_ping_error_to_service_unavailable(
        self, buffer_stub_factory
    ):
        with allure.step("Подготовить буфер, падающий при ping"):
            buffer = buffer_stub_factory(
                ping_error=BufferException("redis down")
            )

        with allure.step("Вызвать обработчик health и ожидать HTTPException"):
            with pytest.raises(HTTPException) as exc_info:
                await health(buffer=buffer)

        with allure.step("Проверить код 503 и сообщение об ошибке"):
            assert exc_info.value.status_code == 503
            assert exc_info.value.detail == "Failed connect to buffer"

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title(
        "GET /health возвращает 200 через ASGI-приложение [INTEGRATION]"
    )
    async def test_health_endpoint(self, buffer_stub_factory):
        with allure.step("Подготовить доступный буфер"):
            buffer = buffer_stub_factory()

        with allure.step("Выполнить запрос к ASGI-приложению"):
            response = await _get_health(buffer)

        with allure.step("Проверить ответ"):
            assert response.status_code == 200
            assert response.json() == 200

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title(
        "GET /health отдаёт HTTP 503 при недоступном буфере [INTEGRATION]"
    )
    async def test_health_endpoint_returns_service_unavailable(
        self, buffer_stub_factory
    ):
        with allure.step("Подготовить буфер, падающий при ping"):
            buffer = buffer_stub_factory(
                ping_error=BufferException("redis down")
            )

        with allure.step("Выполнить запрос к ASGI-приложению"):
            response = await _get_health(buffer)

        with allure.step("Проверить код ответа и detail"):
            assert response.status_code == 503
            assert response.json() == {"detail": "Failed connect to buffer"}
