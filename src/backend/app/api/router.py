from fastapi import APIRouter
from app.api.routes import health, records, predictions, schedule, backups

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(records.router)
api_router.include_router(predictions.router)
api_router.include_router(schedule.router)
api_router.include_router(backups.router)
