from fastapi import FastAPI

from intake.routes import intake_router, service_router

app = FastAPI()
app.include_router(intake_router)
app.include_router(service_router)
