from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict

from models.metrics import Metrics, MetricsDTO
from models.enums import ServerTypes


@dataclass
class ServerStats:
	server_name:str # Уникальное имя сервера
	server_type:ServerTypes # production, staging, test
	metrics:Metrics # Набор метрик


class ServerStatsDTO(BaseModel):
    model_config = ConfigDict(
          from_attributes=True,
          frozen=True
    )

    server_name:str
    server_type:ServerTypes
    metrics:MetricsDTO
