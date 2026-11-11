from dataclasses import dataclass
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from .enums import ServerTypes


@dataclass
class Metrics:
	cpu_load:float # Загрузка CPU (0.54)
	ram_load:float # Загрузка RAM (0.67)
	disk_read:int # Скорость чтения kb/s
	disk_write:int # Скорость записи kb/s
	load_average:list[float] # la, [0.59, 0.50, 0.65]
	timestamp:datetime # Временная метка


class MetricsDTO(BaseModel):
    model_config = ConfigDict(
          from_attributes=True,
          frozen=True
    )

    cpu_load:float
    ram_load:float
    disk_read:int
    disk_write:int
    load_average:list[float]
    timestamp:datetime


@dataclass
class ServerStats:
      server_name:str # Уникальное имя сервера
      server_type:ServerTypes # production, staging, test
      seq:int # Порядковый номер заявки 
      metrics:Metrics # Набор метрик


class ServerStatsDTO(BaseModel):
    model_config = ConfigDict(
          from_attributes=True,
          frozen=True
    )

    server_name:str
    server_type:ServerTypes
    seq:int
    metrics:MetricsDTO
