from datetime import datetime
from fastapi import APIRouter, Depends
from models import ServerStatsDTO, Bid

from intake.clients.redis_client import RedisBuffer
from intake.clients.buffer_client import BufferClient

intake_router = APIRouter()

@intake_router.post('/collect', status_code=201)
async def collect_metrics(stats:ServerStatsDTO):
    stats_obj = stats.to_obj()

    bid = Bid(
        source_name=stats_obj.server_name,
        source_type=stats_obj.server_type,
        seq=stats_obj.seq,
        time_in=datetime.now(),
        stats=stats_obj.metrics
    )

