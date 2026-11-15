from contextlib import asynccontextmanager

from fastapi import FastAPI

from intake.config import create_buffer
from intake.routes import intake_router, service_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    buffer = create_buffer()
    await buffer.ping()
    app.state.buffer = buffer
    try:
        yield
    finally:
        await buffer.aclose()


app = FastAPI(lifespan=lifespan)
app.include_router(intake_router)
app.include_router(service_router)
