import allure
import httpx
import pytest

from intake.main import app
from intake.routes.service import health


class TestHealthRoute:
    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("health возвращает 200 [UNIT]")
    async def test_health_returns_200(self):
        with allure.step("Вызвать обработчик health"):
            result = await health()

        with allure.step("Проверить код ответа"):
            assert result == 200

    @pytest.mark.integration
    @pytest.mark.asyncio
    @allure.title("GET /health возвращает 200 через ASGI-приложение [INTEGRATION]")
    async def test_health_endpoint(self):
        with allure.step("Выполнить запрос к ASGI-приложению"):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://intake.test"
            ) as client:
                response = await client.get("/health")

        with allure.step("Проверить ответ"):
            assert response.status_code == 200
            assert response.json() == 200
