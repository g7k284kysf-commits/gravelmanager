from app.api.deps import CurrentUser, DbSession
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import calculate_dashboard
from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard(db: DbSession, user: CurrentUser) -> DashboardResponse:
    return calculate_dashboard(db, user.id)
