from typing import Annotated

from app.api.deps import CurrentTenant, DbSession
from app.models import Competition, Goal, Season
from app.schemas.planning import (
    CompetitionInput,
    CompetitionResponse,
    GoalInput,
    GoalResponse,
    SeasonInput,
    SeasonResponse,
)
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/planning", tags=["Goal and Competition Planning"])
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def owned[PlanningModel: (Season, Goal, Competition)](
    db: Session,
    model: type[PlanningModel],
    entity_id: int,
    tenant_id: int,
    athlete_id: int,
) -> PlanningModel:
    entity = db.scalar(
        select(model).where(
            model.id == entity_id,
            model.tenant_id == tenant_id,
            model.athlete_id == athlete_id,
        )
    )
    if entity is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return entity


def validate_season(db: Session, season_id: int, tenant: CurrentTenant) -> Season:
    return owned(db, Season, season_id, tenant.tenant_id, tenant.athlete_id)


def validate_goal_links(db: Session, payload: GoalInput, tenant: CurrentTenant) -> None:
    if payload.season_id is not None:
        validate_season(db, payload.season_id, tenant)
    if payload.parent_goal_id is not None:
        parent = owned(db, Goal, payload.parent_goal_id, tenant.tenant_id, tenant.athlete_id)
        if (
            payload.season_id is not None
            and parent.season_id is not None
            and payload.season_id != parent.season_id
        ):
            raise HTTPException(
                status_code=422,
                detail="A child goal must belong to the same season as its parent",
            )


def validate_goal_hierarchy(
    db: Session,
    *,
    goal_id: int | None,
    parent_goal_id: int | None,
    tenant: CurrentTenant,
) -> None:
    """Walk the prospective ancestry iteratively and reject direct or indirect cycles."""
    current_id = parent_goal_id
    visited: set[int] = set()
    while current_id is not None:
        if current_id == goal_id or current_id in visited:
            raise HTTPException(status_code=422, detail="Goal hierarchy cannot contain a cycle")
        visited.add(current_id)
        current = owned(db, Goal, current_id, tenant.tenant_id, tenant.athlete_id)
        current_id = current.parent_goal_id


def validate_competition_links(
    db: Session, payload: CompetitionInput, tenant: CurrentTenant
) -> None:
    validate_season(db, payload.season_id, tenant)
    if payload.goal_id is not None:
        goal = owned(db, Goal, payload.goal_id, tenant.tenant_id, tenant.athlete_id)
        if goal.season_id is not None and goal.season_id != payload.season_id:
            raise HTTPException(
                status_code=422,
                detail="Competition goal must belong to the selected season",
            )


@router.get("/seasons", response_model=list[SeasonResponse])
def list_seasons(
    db: DbSession,
    tenant: CurrentTenant,
    limit: Limit = 50,
    offset: Offset = 0,
) -> list[Season]:
    return list(
        db.scalars(
            select(Season)
            .where(
                Season.tenant_id == tenant.tenant_id,
                Season.athlete_id == tenant.athlete_id,
            )
            .order_by(Season.start_date.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@router.post("/seasons", response_model=SeasonResponse, status_code=status.HTTP_201_CREATED)
def create_season(payload: SeasonInput, db: DbSession, tenant: CurrentTenant) -> Season:
    season = Season(
        tenant_id=tenant.tenant_id,
        athlete_id=tenant.athlete_id,
        **payload.model_dump(),
    )
    db.add(season)
    db.commit()
    db.refresh(season)
    return season


@router.get("/seasons/{season_id}", response_model=SeasonResponse)
def get_season(season_id: int, db: DbSession, tenant: CurrentTenant) -> Season:
    return owned(db, Season, season_id, tenant.tenant_id, tenant.athlete_id)


@router.put("/seasons/{season_id}", response_model=SeasonResponse)
def update_season(
    season_id: int, payload: SeasonInput, db: DbSession, tenant: CurrentTenant
) -> Season:
    season = owned(db, Season, season_id, tenant.tenant_id, tenant.athlete_id)
    for field, value in payload.model_dump().items():
        setattr(season, field, value)
    db.commit()
    db.refresh(season)
    return season


@router.delete("/seasons/{season_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_season(season_id: int, db: DbSession, tenant: CurrentTenant) -> None:
    db.delete(owned(db, Season, season_id, tenant.tenant_id, tenant.athlete_id))
    db.commit()


@router.get("/goals", response_model=list[GoalResponse])
def list_goals(
    db: DbSession,
    tenant: CurrentTenant,
    limit: Limit = 50,
    offset: Offset = 0,
) -> list[Goal]:
    return list(
        db.scalars(
            select(Goal)
            .where(
                Goal.tenant_id == tenant.tenant_id,
                Goal.athlete_id == tenant.athlete_id,
            )
            .order_by(Goal.target_date, Goal.id)
            .limit(limit)
            .offset(offset)
        )
    )


@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(payload: GoalInput, db: DbSession, tenant: CurrentTenant) -> Goal:
    validate_goal_links(db, payload, tenant)
    validate_goal_hierarchy(db, goal_id=None, parent_goal_id=payload.parent_goal_id, tenant=tenant)
    goal = Goal(
        tenant_id=tenant.tenant_id,
        athlete_id=tenant.athlete_id,
        **payload.model_dump(),
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.get("/goals/{goal_id}", response_model=GoalResponse)
def get_goal(goal_id: int, db: DbSession, tenant: CurrentTenant) -> Goal:
    return owned(db, Goal, goal_id, tenant.tenant_id, tenant.athlete_id)


@router.put("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(goal_id: int, payload: GoalInput, db: DbSession, tenant: CurrentTenant) -> Goal:
    goal = owned(db, Goal, goal_id, tenant.tenant_id, tenant.athlete_id)
    validate_goal_links(db, payload, tenant)
    validate_goal_hierarchy(
        db, goal_id=goal.id, parent_goal_id=payload.parent_goal_id, tenant=tenant
    )
    for field, value in payload.model_dump().items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: int, db: DbSession, tenant: CurrentTenant) -> None:
    db.delete(owned(db, Goal, goal_id, tenant.tenant_id, tenant.athlete_id))
    db.commit()


@router.get("/competitions", response_model=list[CompetitionResponse])
def list_competitions(
    db: DbSession,
    tenant: CurrentTenant,
    limit: Limit = 50,
    offset: Offset = 0,
) -> list[Competition]:
    return list(
        db.scalars(
            select(Competition)
            .where(
                Competition.tenant_id == tenant.tenant_id,
                Competition.athlete_id == tenant.athlete_id,
            )
            .order_by(Competition.start_date)
            .limit(limit)
            .offset(offset)
        )
    )


@router.post(
    "/competitions",
    response_model=CompetitionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_competition(
    payload: CompetitionInput, db: DbSession, tenant: CurrentTenant
) -> Competition:
    validate_competition_links(db, payload, tenant)
    competition = Competition(
        tenant_id=tenant.tenant_id,
        athlete_id=tenant.athlete_id,
        **payload.model_dump(),
    )
    db.add(competition)
    db.commit()
    db.refresh(competition)
    return competition


@router.get("/competitions/{competition_id}", response_model=CompetitionResponse)
def get_competition(competition_id: int, db: DbSession, tenant: CurrentTenant) -> Competition:
    return owned(db, Competition, competition_id, tenant.tenant_id, tenant.athlete_id)


@router.put("/competitions/{competition_id}", response_model=CompetitionResponse)
def update_competition(
    competition_id: int,
    payload: CompetitionInput,
    db: DbSession,
    tenant: CurrentTenant,
) -> Competition:
    competition = owned(db, Competition, competition_id, tenant.tenant_id, tenant.athlete_id)
    validate_competition_links(db, payload, tenant)
    for field, value in payload.model_dump().items():
        setattr(competition, field, value)
    db.commit()
    db.refresh(competition)
    return competition


@router.delete("/competitions/{competition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competition(competition_id: int, db: DbSession, tenant: CurrentTenant) -> None:
    db.delete(owned(db, Competition, competition_id, tenant.tenant_id, tenant.athlete_id))
    db.commit()
