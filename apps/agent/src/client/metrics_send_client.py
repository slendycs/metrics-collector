import requests

from config import get_settings
from models import ServerStatsDTO, ServerStats

class Client:
    _POST_ENDPOINT:str = '/collect'

    def post(self, stats:ServerStats) -> None:
        """
        Отправляет POST запрос с пакетом метрик к серверу

        Args:
            stats (ServerStats): Пакет метрик
        
        Raises:
            HTTPExeption: При ошибках сети
        """
        dto = ServerStatsDTO.model_validate(stats)
        payload = dto.model_dump(mode='json')
        url = get_settings().reception_service_url.rstrip('/') + self._POST_ENDPOINT

        response = requests.post(
            url, 
            json=payload
        )
        response.raise_for_status()
