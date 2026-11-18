from unittest.mock import AsyncMock, MagicMock, patch

import allure
import httpx
import pytest

from intake.stats import stats_client as stats_client_module
from intake.stats.stats_client import StatsClient
from models import PutResult, PutResultDTO, ServerTypes


def _make_result() -> PutResult:
    """Результат обработки заявки, как его вернул бы буфер."""
    return PutResult(
        accepted=True,
        bid_id=1,
        seq=0,
        source_name="agent-1",
        source_type=ServerTypes.TEST,
        slot=1,
    )


def _expected_payload(result: PutResult) -> dict:
    """JSON-payload, который клиент обязан отправить в статистику."""
    return PutResultDTO.model_validate(result).model_dump(mode="json")


def _make_http_status_error() -> httpx.HTTPStatusError:
    """Собирает настоящий HTTPStatusError, как при ответе с ошибкой."""
    request = httpx.Request("POST", "http://stats.test/intake/take")
    response = httpx.Response(500, request=request)
    return httpx.HTTPStatusError("server error", request=request, response=response)


class _StubAsyncClient:
    """Заглушка httpx.AsyncClient: асинхронный контекстный менеджер с post."""

    def __init__(self, response: MagicMock | None = None) -> None:
        self.response = response
        self.post = AsyncMock(return_value=response)
        self.entered = False

    async def __aenter__(self) -> "_StubAsyncClient":
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> bool:
        return False


class TestStatsClient:
    @pytest.mark.unit
    @pytest.mark.asyncio
    @allure.title("notify отправляет POST с результатом заявки в статистику [UNIT]")
    async def test_posts_result_to_stats_server(self, monkeypatch):
        with allure.step("Подготовить результат и заглушку HTTP-клиента"):
            result = _make_result()
            response = MagicMock()
            client = _StubAsyncClient(response=response)
            monkeypatch.setattr(
                stats_client_module.settings,
                "stats_server_url",
                "http://stats.test",
            )

        with allure.step("Вызвать notify с подменённым AsyncClient"):
            with patch(
                "intake.stats.stats_client.AsyncClient", return_value=client
            ):
                await StatsClient().notify(result)

        with allure.step("Проверить URL и json-payload POST-запроса"):
            client.post.assert_awaited_once_with(
                "http://stats.test/intake/take",
                json=_expected_payload(result),
            )

        with allure.step("Проверить вызов raise_for_status у ответа"):
            response.raise_for_status.assert_called_once_with()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "base_url",
        [
            pytest.param("http://stats.test/", id="single-slash"),
            pytest.param("http://stats.test///", id="many-slashes"),
        ],
    )
    @allure.title(
        "Завершающие слэши адреса {base_url} не дают двойной слэш в URL [UNIT]"
    )
    async def test_strips_trailing_slashes_from_stats_url(self, monkeypatch, base_url):
        with allure.step("Подготовить заглушку HTTP-клиента и адрес со слэшами"):
            result = _make_result()
            client = _StubAsyncClient(response=MagicMock())
            monkeypatch.setattr(
                stats_client_module.settings, "stats_server_url", base_url
            )

        with allure.step("Вызвать notify"):
            with patch(
                "intake.stats.stats_client.AsyncClient", return_value=client
            ):
                await StatsClient().notify(result)

        with allure.step("Проверить, что URL собран без двойного слэша"):
            url = client.post.await_args.args[0]
            assert url == "http://stats.test/intake/take"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error_factory", "error_name"),
        [
            pytest.param(
                _make_http_status_error, "HTTPStatusError", id="status-error"
            ),
            pytest.param(
                lambda: httpx.HTTPError("connection lost"), "HTTPError", id="http-error"
            ),
        ],
    )
    @allure.title("notify пробрасывает {error_name} из raise_for_status [UNIT]")
    async def test_propagates_http_error(self, monkeypatch, error_factory, error_name):
        with allure.step("Подготовить ответ, падающий при raise_for_status"):
            result = _make_result()
            error = error_factory()
            response = MagicMock()
            response.raise_for_status.side_effect = error
            client = _StubAsyncClient(response=response)
            monkeypatch.setattr(
                stats_client_module.settings,
                "stats_server_url",
                "http://stats.test",
            )

        with allure.step("Вызвать notify и ожидать проброс ошибки"):
            with patch(
                "intake.stats.stats_client.AsyncClient", return_value=client
            ):
                with pytest.raises(type(error)) as exc_info:
                    await StatsClient().notify(result)

        with allure.step("Проверить, что наружу ушла исходная ошибка"):
            assert exc_info.value is error