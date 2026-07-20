from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.athlete import AthleteProfile
    from app.models.training import Training


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    profile: Mapped["AthleteProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    trainings: Mapped[list["Training"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
