from app.api.routes import (
    athlete,
    auth,
    dashboard,
    imports,
    integrations,
    performance,
    planning,
    trainings,
)
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(athlete.router)
api_router.include_router(trainings.router)
api_router.include_router(dashboard.router)
api_router.include_router(performance.router)
api_router.include_router(planning.router)
api_router.include_router(integrations.router)
api_router.include_router(imports.router)
