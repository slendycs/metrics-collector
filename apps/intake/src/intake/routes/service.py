from fastapi import APIRouter

service_router = APIRouter(tags=['Service endpoints'])


@service_router.get('/health', status_code=200)
async def health() -> int:
    return 200
