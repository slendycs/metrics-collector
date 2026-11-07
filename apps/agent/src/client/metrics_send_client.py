import requests

from config.config import get_settings
from models.server_stats import ServerStatsDTO, ServerStats

class Client:
    _POST_ENDPOINT:str = '/collect'
    _base_url:str = get_settings().reception_service_url.rstrip('/')

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

        response = requests.post(
            self._base_url + self._POST_ENDPOINT, 
            json=payload
        )
        response.raise_for_status()
