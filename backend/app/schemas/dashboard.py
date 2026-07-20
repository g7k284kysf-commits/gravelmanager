from pydantic import BaseModel


class DashboardResponse(BaseModel):
    ftp: int | None
    ctl: float
    atl: float
    tsb: float
    weekly_hours: float
    weekly_tss: float
