from app.api.deps import CurrentUser, DbSession
from app.models import AthleteProfile
from app.schemas.athlete import AthleteProfileInput, AthleteProfileResponse
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

router = APIRouter(prefix="/athlete", tags=["Athlete"])


@router.get("/profile", response_model=AthleteProfileResponse)
def get_profile(db: DbSession, user: CurrentUser) -> AthleteProfile:
    profile = db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user.id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Athlete profile not found")
    return profile


@router.put("/profile", response_model=AthleteProfileResponse)
def upsert_profile(
    payload: AthleteProfileInput, db: DbSession, user: CurrentUser
) -> AthleteProfile:
    profile = db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user.id))
    if profile is None:
        profile = AthleteProfile(user_id=user.id, **payload.model_dump())
        db.add(profile)
    else:
        for field, value in payload.model_dump().items():
            setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile
