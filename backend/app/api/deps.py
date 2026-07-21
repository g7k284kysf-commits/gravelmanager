from typing import Annotated

import jwt
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User
from app.services.tenancy import TenantContext, active_tenant_context
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

bearer = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if credentials is None:
        raise error
    try:
        user_id = int(decode_access_token(credentials.credentials))
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise error from exc
    user = db.get(User, user_id)
    if user is None:
        raise error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_tenant_context(db: DbSession, user: CurrentUser) -> TenantContext:
    context = active_tenant_context(db, user)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active tenant membership is available",
        )
    return context


CurrentTenant = Annotated[TenantContext, Depends(get_tenant_context)]
