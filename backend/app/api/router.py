from app.api.routes import athlete, auth, dashboard, performance, trainings
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(athlete.router)
api_router.include_router(trainings.router)
api_router.include_router(dashboard.router)
api_router.include_router(performance.router)
