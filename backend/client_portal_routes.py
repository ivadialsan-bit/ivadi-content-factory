from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth_routes import require_roles
from models import (
    User,
    Client,
    ClientProfile,
    ClientBriefFile,
    ClientIntelligence,
    ClientStrategy,
    ClientContentPlan,
)

router = APIRouter(prefix="/api/client-portal", tags=["client-portal"])


def get_portal_client(current_user: User, db: Session):
    if not current_user.client_id:
        raise HTTPException(status_code=403, detail="Клиентский кабинет не привязан")

    client = db.query(Client).filter(
        Client.id == current_user.client_id,
        Client.tenant_id == current_user.tenant_id
    ).first()

    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    return client


@router.get("/me")
def portal_me(
    current_user: User = Depends(require_roles("CLIENT")),
    db: Session = Depends(get_db),
):
    client = get_portal_client(current_user, db)

    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role,
            "tenant_id": current_user.tenant_id,
            "client_id": current_user.client_id,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
        },
        "client": {
            "id": client.id,
            "name": client.name,
            "brand": client.brand,
            "niche": client.niche,
            "status": client.status,
        }
    }


@router.get("/profile")
def portal_profile(
    current_user: User = Depends(require_roles("CLIENT")),
    db: Session = Depends(get_db),
):
    client = get_portal_client(current_user, db)

    return db.query(ClientProfile).filter(
        ClientProfile.client_id == client.id,
        ClientProfile.tenant_id == current_user.tenant_id
    ).first()


@router.get("/intelligence")
def portal_intelligence(
    current_user: User = Depends(require_roles("CLIENT")),
    db: Session = Depends(get_db),
):
    client = get_portal_client(current_user, db)

    return db.query(ClientIntelligence).filter(
        ClientIntelligence.client_id == client.id,
        ClientIntelligence.tenant_id == current_user.tenant_id
    ).first()


@router.get("/strategy")
def portal_strategy(
    current_user: User = Depends(require_roles("CLIENT")),
    db: Session = Depends(get_db),
):
    client = get_portal_client(current_user, db)

    return db.query(ClientStrategy).filter(
        ClientStrategy.client_id == client.id,
        ClientStrategy.tenant_id == current_user.tenant_id
    ).first()


@router.get("/content-plan/latest")
def portal_latest_content_plan(
    current_user: User = Depends(require_roles("CLIENT")),
    db: Session = Depends(get_db),
):
    client = get_portal_client(current_user, db)

    return db.query(ClientContentPlan).filter(
        ClientContentPlan.client_id == client.id,
        ClientContentPlan.tenant_id == current_user.tenant_id
    ).order_by(ClientContentPlan.created_at.desc()).first()


@router.get("/briefs")
def portal_briefs(
    current_user: User = Depends(require_roles("CLIENT")),
    db: Session = Depends(get_db),
):
    client = get_portal_client(current_user, db)

    return db.query(ClientBriefFile).filter(
        ClientBriefFile.client_id == client.id,
        ClientBriefFile.tenant_id == current_user.tenant_id
    ).order_by(ClientBriefFile.created_at.desc()).all()
