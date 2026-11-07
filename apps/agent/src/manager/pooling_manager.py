from time import sleep
from random import randint
from requests import HTTPError
from pydantic import ValidationError
import psutil

from client.metrics_send_client import Client
from config.config import get_settings
from config.logger import logger
from exporter.metrics_exporter import MetricsExporter



class PoolingManager:
    _client = Client()
    _exporter = MetricsExporter()
    _timeout_min:int = get_settings().timeout_min
    _timeout_max:int = get_settings().timeout_max


    def pooling(self) -> None:
        while True:
            try:
                metrics_package = self._exporter.collect()
                self._client.post(metrics_package)
                logger.info(f'The metrics package was successfully sent')

            except HTTPError as err:
                logger.error(f'An error occurred while sending metrics: {str(err)}')
            except (ValueError, ValidationError, TypeError) as err:
                logger.error(f'An error occurred while attempting to parse the metrics: {str(err)}')
            except (OSError, psutil.Error) as err:
                logger.critical(f'Unable to access /proc: {err}')


            sleep(randint(self._timeout_min, self._timeout_max))
