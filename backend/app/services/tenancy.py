from dataclasses import dataclass

from app.models import Tenant, TenantMembership, User
from app.models.tenant import MembershipRole, MembershipStatus, TenantStatus, TenantType
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class TenantContext:
    user_id: int
    tenant_id: int
    athlete_id: int
    role: MembershipRole


def create_personal_tenant(db: Session, user: User) -> TenantMembership:
    tenant = Tenant(
        name=f"{user.email}'s personal workspace",
        slug=f"personal-{user.id}",
        tenant_type=TenantType.PERSONAL,
        status=TenantStatus.ACTIVE,
    )
    db.add(tenant)
    db.flush()
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user.id,
        role=MembershipRole.OWNER,
        status=MembershipStatus.ACTIVE,
    )
    db.add(membership)
    db.flush()
    return membership


def active_tenant_context(db: Session, user: User) -> TenantContext | None:
    membership = db.scalar(
        select(TenantMembership)
        .join(Tenant, Tenant.id == TenantMembership.tenant_id)
        .where(
            TenantMembership.user_id == user.id,
            TenantMembership.status == MembershipStatus.ACTIVE,
            Tenant.status == TenantStatus.ACTIVE,
        )
        .order_by(TenantMembership.id)
        .limit(1)
    )
    if membership is None:
        return None
    return TenantContext(
        user_id=user.id,
        tenant_id=membership.tenant_id,
        athlete_id=user.id,
        role=membership.role,
    )
