from unittest.mock import MagicMock, patch

import allure
import pytest
import requests

from client import Client
from config import get_settings
from models import ServerStatsDTO


class TestClient:
    @pytest.mark.unit
    @allure.title("Базовый URL клиента не содержит завершающего слеша [UNIT]")
    def test_base_url_has_no_trailing_slash(self):
        with allure.step("Сравнить базовый URL клиента с настройкой сервиса приёма"):
            assert Client._base_url == get_settings().reception_service_url.rstrip("/")

    @pytest.mark.unit
    @allure.title("post отправляет DTO метрик на /collect [UNIT]")
    def test_post_sends_dto_payload(self, client, server_stats):
        with allure.step("Подготовить клиент и мок HTTP-ответа"):
            client._base_url = "http://reception.test"
            response = MagicMock()

        with allure.step("Отправить пакет метрик через POST"):
            with patch(
                "client.metrics_send_client.requests.post", return_value=response
            ) as post:
                client.post(server_stats)

        with allure.step("Проверить URL и JSON-payload запроса"):
            expected_payload = ServerStatsDTO.model_validate(server_stats).model_dump(
                mode="json"
            )
            post.assert_called_once_with(
                "http://reception.test/collect", json=expected_payload
            )

        with allure.step("Проверить вызов raise_for_status"):
            response.raise_for_status.assert_called_once_with()

    @pytest.mark.unit
    @allure.title("post пробрасывает HTTPError от сервера [UNIT]")
    def test_post_propagates_http_error(self, client, server_stats):
        with allure.step("Смоделировать HTTP-ответ с ошибкой"):
            response = MagicMock()
            response.raise_for_status.side_effect = requests.HTTPError(
                "500 Server Error"
            )

        with allure.step("Отправить метрики и ожидать исключение"):
            with (
                patch(
                    "client.metrics_send_client.requests.post", return_value=response
                ),
                pytest.raises(requests.HTTPError, match="500 Server Error"),
            ):
                client.post(server_stats)

    @pytest.mark.unit
    @allure.title("post пробрасывает ConnectionError при недоступности сервера [UNIT]")
    def test_post_propagates_connection_error(self, client, server_stats):
        with allure.step("Смоделировать сетевую ошибку"):
            error = requests.ConnectionError("connection refused")

        with allure.step("Отправить метрики и ожидать исключение"):
            with (
                patch(
                    "client.metrics_send_client.requests.post", side_effect=error
                ),
                pytest.raises(requests.ConnectionError, match="connection refused"),
            ):
                client.post(server_stats)

    @pytest.mark.integration
    @allure.title("post доставляет метрики на реальный HTTP-сервер [INTEGRATION]")
    def test_post_reaches_real_http_server(self, client, server_stats, http_server):
        with allure.step("Направить клиент на локальный HTTP-сервер"):
            host, port = http_server.server_address[:2]
            client._base_url = f"http://{host}:{port}"

        with allure.step("Отправить пакет метрик"):
            client.post(server_stats)

        with allure.step("Проверить полученный сервером запрос"):
            assert len(http_server.requests) == 1
            received = http_server.requests[0]
            assert received["path"] == "/collect"
            assert received["headers"]["Content-Type"] == "application/json"
            assert received["json"] == ServerStatsDTO.model_validate(
                server_stats
            ).model_dump(mode="json")

    @pytest.mark.integration
    @allure.title("post поднимает HTTPError на реальном ответе 500 [INTEGRATION]")
    def test_post_raises_on_real_server_error(self, client, server_stats, http_server):
        with allure.step("Настроить сервер на ответ 500 и направить к нему клиент"):
            host, port = http_server.server_address[:2]
            http_server.response_status = 500
            client._base_url = f"http://{host}:{port}"

        with allure.step("Отправить метрики и ожидать HTTPError"):
            with pytest.raises(requests.HTTPError):
                client.post(server_stats)
