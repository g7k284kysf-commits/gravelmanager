from app.api.deps import CurrentTenant, CurrentUser, DbSession
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import calculate_dashboard
from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard(db: DbSession, user: CurrentUser, tenant: CurrentTenant) -> DashboardResponse:
    return calculate_dashboard(db, tenant.tenant_id, user.id)
