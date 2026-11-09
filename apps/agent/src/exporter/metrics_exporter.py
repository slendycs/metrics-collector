import psutil
import time
from datetime import datetime

from config import get_settings
from models import ServerStats, Metrics, ServerTypes


class MetricsExporter:
    _server_name:str = get_settings().server_name
    _server_type:ServerTypes = get_settings().server_type
    _interval:float = 1.0


    def _read_disk_bytes(self) -> tuple[int, int]:
        counters = psutil.disk_io_counters(perdisk=False)
        if counters is None:
            return 0, 0

        return counters.read_bytes, counters.write_bytes


    def collect(self) -> ServerStats:
        """
        Собирает метрики сервера: CPU, RAM, disk I/O и load average.

        Скорость чтения и записи диска считается за интервал `self._interval`.

        Returns:
            ServerStats: объект с именем сервера, типом сервера и метриками.

        Raises:
            psutil.Error: при ошибке получения метрик через psutil.
            OSError: при ошибке доступа к /proc.
            ValueError: при некорректных значениях метрик.
            TypeError: при неожиданном типе данных.
            pydantic.ValidationError: при ошибке валидации моделей.
        """
        read_before, write_before = self._read_disk_bytes()
        started_time = time.monotonic()
        cpu_load = psutil.cpu_percent(interval=self._interval)
        elapsed = max(time.monotonic() - started_time, 1e-6)
        read_after, write_after = self._read_disk_bytes()

        disk_read = int(round(max(0.0, (read_after - read_before) / 1024.0 / elapsed)))
        disk_write = int(round(max(0.0,(write_after - write_before) / 1024.0 / elapsed)))

        metrics_package = Metrics(
            cpu_load=cpu_load,
            ram_load=psutil.virtual_memory().percent,
            disk_read=disk_read,
            disk_write=disk_write,
            load_average=list(psutil.getloadavg()),
            timestamp=datetime.now()
        )

        return ServerStats(
            server_name=self._server_name,
            server_type=self._server_type,
            metrics=metrics_package
        )
