import logging
from datetime import date

from app.api.deps import CurrentUser, DbSession
from app.models import Training
from app.schemas.training import TrainingInput, TrainingResponse
from app.services.performance import PerformanceCalculationService
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

router = APIRouter(prefix="/trainings", tags=["Training"])
logger = logging.getLogger(__name__)


def commit_with_recalculation(db: DbSession, user_id: int, start_date: date) -> None:
    try:
        db.flush()
        PerformanceCalculationService(db).recalculate(user_id, start_date)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Training mutation and performance recalculation failed for user %s", user_id
        )
        raise HTTPException(
            status_code=500, detail="Training changes could not be applied safely"
        ) from exc


@router.get("", response_model=list[TrainingResponse])
def list_trainings(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Training]:
    return list(
        db.scalars(
            select(Training)
            .where(Training.user_id == user.id)
            .order_by(Training.date.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@router.post("", response_model=TrainingResponse, status_code=status.HTTP_201_CREATED)
def create_training(payload: TrainingInput, db: DbSession, user: CurrentUser) -> Training:
    training = Training(user_id=user.id, **payload.model_dump())
    db.add(training)
    commit_with_recalculation(db, user.id, payload.date)
    db.refresh(training)
    return training


def owned_training(training_id: int, db: DbSession, user_id: int) -> Training:
    training = db.scalar(
        select(Training).where(Training.id == training_id, Training.user_id == user_id)
    )
    if training is None:
        raise HTTPException(status_code=404, detail="Training not found")
    return training


@router.get("/{training_id}", response_model=TrainingResponse)
def get_training(training_id: int, db: DbSession, user: CurrentUser) -> Training:
    return owned_training(training_id, db, user.id)


@router.put("/{training_id}", response_model=TrainingResponse)
def update_training(
    training_id: int, payload: TrainingInput, db: DbSession, user: CurrentUser
) -> Training:
    training = owned_training(training_id, db, user.id)
    original_date = training.date
    for field, value in payload.model_dump().items():
        setattr(training, field, value)
    commit_with_recalculation(db, user.id, min(original_date, payload.date))
    db.refresh(training)
    return training


@router.delete("/{training_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_training(training_id: int, db: DbSession, user: CurrentUser) -> None:
    training = owned_training(training_id, db, user.id)
    deleted_date = training.date
    db.delete(training)
    commit_with_recalculation(db, user.id, deleted_date)
