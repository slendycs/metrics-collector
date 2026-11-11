from fastapi import APIRouter, Depends
from models import ServerStats

from clients.buffer_client import BufferClient

intake_router = APIRouter()

@intake_router.post('/collect', status_code=201)
async def collect_metrics(stats:ServerStats, buffer:BufferClient = Depends()):
    return 201