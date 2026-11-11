from datetime import datetime
from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict

from .enums import ServerTypes
from .metrics import Metrics, MetricsDTO


@dataclass
class Bid:
    id:int # id заявки
    source_name:str # Имя сервера
    source_type:ServerTypes # Тип сервера
    seq:int # Порядковый номер заявки внутри источника
    time_in:datetime # 
    stats:Metrics


class BidDTO(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        frozen=True
    )

    id:int
    source_name:str
    source_type:ServerTypes
    seq:int
    time_in:datetime
    stats:MetricsDTO


@dataclass
class PutResult:
    accepted:bool # Статус заявки 
    slot:int # Номер места в буфере
    bid_id:int # id заявки
    seq:int # Порядковый номер заявки от источника


class PutResultDTO(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        frozen=True
    )

    accepted:bool
    slot:int
    bid_id:int
    seq:int
