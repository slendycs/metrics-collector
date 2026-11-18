from httpx import AsyncClient

from models import PutResult, PutResultDTO

from intake.config import settings

class StatsClient:
    _STATS_ENDPOINT:str = '/intake/take'

    async def notify(self, post_result:PutResult) -> None:
        """
        Отпраляет данные об обработанной заявке на сервер статистики

        Args:
            post_result (PutResult): Результат обработки заявки

        Raises:
            HTTPError: при ошибках сети, не 200-го статус кода
        """
        async with AsyncClient() as client:
            dto = PutResultDTO.model_validate(post_result)
            payload = dto.model_dump(mode='json')
            url = settings.stats_server_url.rstrip('/') + self._STATS_ENDPOINT

            response = await client.post(url, json=payload)
            response.raise_for_status()
