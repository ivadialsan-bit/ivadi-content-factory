from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from auth_routes import require_roles
from models import User, Tenant, Client
from security import hash_password


router = APIRouter(prefix="/api/admin", tags=["admin"])


ALLOWED_ROLES = {"SUPER_ADMIN", "ADMIN", "MANAGER", "CLIENT"}


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "CLIENT"
    tenant_id: int | None = None
    client_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None


class UserUpdateRequest(BaseModel):
    role: str | None = None
    client_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool | None = None


def serialize_user(user: User):
    return {
        "id": user.id,
        "tenant_id": user.tenant_id,
        "client_id": user.client_id,
        "email": user.email,
        "role": user.role,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_email_verified": user.is_email_verified,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def assert_role_allowed(role: str):
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")


def assert_admin_scope(target_user: User, current_user: User):
    if current_user.role == "SUPER_ADMIN":
        return
    if target_user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Cannot manage users from another tenant")
    if target_user.role == "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Cannot manage SUPER_ADMIN")


@router.get("/users")
def list_users(
    current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN")),
    db: Session = Depends(get_db),
):
    q = db.query(User)

    if current_user.role != "SUPER_ADMIN":
        q = q.filter(User.tenant_id == current_user.tenant_id)

    return [serialize_user(u) for u in q.order_by(User.created_at.desc()).all()]


@router.post("/users")
def create_user(
    payload: UserCreateRequest,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN")),
    db: Session = Depends(get_db),
):
    assert_role_allowed(payload.role)

    if current_user.role != "SUPER_ADMIN":
        tenant_id = current_user.tenant_id
        if payload.role == "SUPER_ADMIN":
            raise HTTPException(status_code=403, detail="ADMIN cannot create SUPER_ADMIN")
    else:
        tenant_id = payload.tenant_id or current_user.tenant_id

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if payload.client_id:
        client = db.query(Client).filter(
            Client.id == payload.client_id,
            Client.tenant_id == tenant_id,
        ).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found in tenant")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="User with this email already exists")

    user = User(
        tenant_id=tenant_id,
        client_id=payload.client_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        first_name=payload.first_name,
        last_name=payload.last_name,
        is_active=True,
        is_email_verified=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return serialize_user(user)


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    assert_admin_scope(user, current_user)

    if payload.role is not None:
        assert_role_allowed(payload.role)
        if current_user.role != "SUPER_ADMIN" and payload.role == "SUPER_ADMIN":
            raise HTTPException(status_code=403, detail="ADMIN cannot assign SUPER_ADMIN")
        user.role = payload.role

    if payload.client_id is not None:
        if payload.client_id:
            client = db.query(Client).filter(
                Client.id == payload.client_id,
                Client.tenant_id == user.tenant_id,
            ).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found in tenant")
        user.client_id = payload.client_id

    if payload.first_name is not None:
        user.first_name = payload.first_name

    if payload.last_name is not None:
        user.last_name = payload.last_name

    if payload.is_active is not None:
        if user.id == current_user.id and payload.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
        user.is_active = payload.is_active

    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return serialize_user(user)


@router.delete("/users/{user_id}")
def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    assert_admin_scope(user, current_user)

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user.is_active = False
    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return serialize_user(user)
