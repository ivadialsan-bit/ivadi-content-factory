from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
from auth_routes import get_current_user, require_roles
from audit import log_event
from models import Client, ClientProject, ClientChannel, ClientGoal, ClientKPI, ClientAccountSnapshot, ClientProfile, ClientBriefFile, ClientIntelligence, ClientStrategy, ClientContentPlan, User
from schemas import (
    ClientCreate,
    ClientUpdate,
    ClientProjectCreate,
    ClientChannelCreate,
    ClientGoalCreate,
    ClientKPICreate,
    ClientAccountSnapshotCreate,
    ClientProfileCreate,
    ClientProfileUpdate,
    ClientIntelligenceUpdate,
)

router = APIRouter(prefix="/api/clients", tags=["clients"])


def get_tenant_client(client_id: int, current_user: User, db: Session):
    return db.query(Client).filter(
        Client.id == client_id,
        Client.tenant_id == current_user.tenant_id
    ).first()




@router.get("")
def get_clients(
    current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")),
    db: Session = Depends(get_db)
):
    return (
        db.query(Client)
        .filter(Client.tenant_id == current_user.tenant_id)
        .order_by(Client.created_at.desc())
        .all()
    )


@router.post("")
def create_client(
    client: ClientCreate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")),
    db: Session = Depends(get_db)
):
    db_client = Client(
        **client.dict(),
        tenant_id=current_user.tenant_id
    )
    db.add(db_client)
    db.commit()
    db.refresh(db_client)

    log_event(
        db=db,
        action="CLIENT_CREATE",
        user=current_user,
        entity_type="client",
        entity_id=db_client.id,
    )

    return db_client


@router.get("/{client_id}")
def get_client(
    client_id: int,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")),
    db: Session = Depends(get_db)
):
    client = get_tenant_client(client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return client


@router.patch("/{client_id}")
def update_client(
    client_id: int,
    update: ClientUpdate,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")),
    db: Session = Depends(get_db)
):
    client = get_tenant_client(client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    for field, value in update.dict(exclude_unset=True).items():
        setattr(client, field, value)

    db.commit()
    db.refresh(client)

    log_event(
        db=db,
        action="CLIENT_UPDATE",
        user=current_user,
        entity_type="client",
        entity_id=client.id,
    )

    return client


@router.delete("/{client_id}")
def delete_client(
    client_id: int,
    current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")),
    db: Session = Depends(get_db)
):
    client = get_tenant_client(client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    db.query(ClientProject).filter(ClientProject.client_id == client_id, ClientProject.tenant_id == current_user.tenant_id).delete()
    db.query(ClientChannel).filter(ClientChannel.client_id == client_id, ClientChannel.tenant_id == current_user.tenant_id).delete()
    db.query(ClientGoal).filter(ClientGoal.client_id == client_id, ClientGoal.tenant_id == current_user.tenant_id).delete()
    db.query(ClientKPI).filter(ClientKPI.client_id == client_id, ClientKPI.tenant_id == current_user.tenant_id).delete()
    db.query(ClientProfile).filter(ClientProfile.client_id == client_id, ClientProfile.tenant_id == current_user.tenant_id).delete()
    db.query(ClientBriefFile).filter(ClientBriefFile.client_id == client_id, ClientBriefFile.tenant_id == current_user.tenant_id).delete()
    db.query(ClientIntelligence).filter(ClientIntelligence.client_id == client_id, ClientIntelligence.tenant_id == current_user.tenant_id).delete()
    db.query(ClientStrategy).filter(ClientStrategy.client_id == client_id, ClientStrategy.tenant_id == current_user.tenant_id).delete()
    db.query(ClientContentPlan).filter(ClientContentPlan.client_id == client_id, ClientContentPlan.tenant_id == current_user.tenant_id).delete()

    db.delete(client)
    db.commit()
    return {"message": "Deleted"}


@router.get("/{client_id}/overview")
def get_client_overview(client_id: int, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    return {
        "client": client,
        "projects": db.query(ClientProject).filter(ClientProject.client_id == client_id, ClientProject.tenant_id == current_user.tenant_id).all(),
        "channels": db.query(ClientChannel).filter(ClientChannel.client_id == client_id, ClientChannel.tenant_id == current_user.tenant_id).all(),
        "goals": db.query(ClientGoal).filter(ClientGoal.client_id == client_id, ClientGoal.tenant_id == current_user.tenant_id).all(),
        "kpis": db.query(ClientKPI).filter(ClientKPI.client_id == client_id, ClientKPI.tenant_id == current_user.tenant_id).all(),
        "account_snapshots": db.query(ClientAccountSnapshot).join(ClientChannel, ClientAccountSnapshot.channel_id == ClientChannel.id).filter(ClientChannel.client_id == client_id, ClientChannel.tenant_id == current_user.tenant_id).order_by(ClientAccountSnapshot.created_at.desc()).all(),
        "profile": db.query(ClientProfile).filter(ClientProfile.client_id == client_id, ClientProfile.tenant_id == current_user.tenant_id).first(),
        "brief_files": db.query(ClientBriefFile).filter(ClientBriefFile.client_id == client_id, ClientBriefFile.tenant_id == current_user.tenant_id).order_by(ClientBriefFile.created_at.desc()).all(),
        "intelligence": db.query(ClientIntelligence).filter(ClientIntelligence.client_id == client_id, ClientIntelligence.tenant_id == current_user.tenant_id).first(),
        "strategy": db.query(ClientStrategy).filter(ClientStrategy.client_id == client_id, ClientStrategy.tenant_id == current_user.tenant_id).first(),
        "content_plan": db.query(ClientContentPlan).filter(ClientContentPlan.client_id == client_id, ClientContentPlan.tenant_id == current_user.tenant_id).order_by(ClientContentPlan.created_at.desc()).first(),
    }


@router.post("/projects")
def create_client_project(project: ClientProjectCreate, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(project.client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    item = ClientProject(**project.dict(), tenant_id=current_user.tenant_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/channels")
def create_client_channel(channel: ClientChannelCreate, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(channel.client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    item = ClientChannel(**channel.dict(), tenant_id=current_user.tenant_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/goals")
def create_client_goal(goal: ClientGoalCreate, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(goal.client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    item = ClientGoal(**goal.dict(), tenant_id=current_user.tenant_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/kpis")
def create_client_kpi(kpi: ClientKPICreate, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(kpi.client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    item = ClientKPI(**kpi.dict(), tenant_id=current_user.tenant_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/channels/{channel_id}/sync")
def sync_client_channel(channel_id: int, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    channel = db.query(ClientChannel).join(Client, ClientChannel.client_id == Client.id).filter(ClientChannel.id == channel_id, Client.tenant_id == current_user.tenant_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Аккаунт клиента не найден")

    from datetime import datetime
    channel.last_sync_at = datetime.utcnow()
    channel.access_status = "synced_manual"
    db.commit()
    db.refresh(channel)

    return {
        "message": "Синхронизация аккаунта зафиксирована",
        "channel_id": channel.id,
        "platform": channel.platform,
        "last_sync_at": channel.last_sync_at
    }


@router.post("/account-snapshots")
def create_account_snapshot(snapshot: ClientAccountSnapshotCreate, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    channel = db.query(ClientChannel).join(Client, ClientChannel.client_id == Client.id).filter(
        ClientChannel.id == snapshot.channel_id,
        Client.tenant_id == current_user.tenant_id
    ).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Канал клиента не найден")

    item = ClientAccountSnapshot(**snapshot.dict(), tenant_id=current_user.tenant_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/channels/{channel_id}/snapshots")
def get_channel_snapshots(channel_id: int, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    return db.query(ClientAccountSnapshot).join(ClientChannel, ClientAccountSnapshot.channel_id == ClientChannel.id).join(Client, ClientChannel.client_id == Client.id).filter(
        ClientAccountSnapshot.channel_id == channel_id,
        Client.tenant_id == current_user.tenant_id
    ).order_by(ClientAccountSnapshot.created_at.desc()).all()


@router.get("/{client_id}/profile")
def get_client_profile(client_id: int, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    profile = db.query(ClientProfile).filter(ClientProfile.client_id == client_id, ClientProfile.tenant_id == current_user.tenant_id).first()
    if not profile:
        return None
    return profile


@router.post("/{client_id}/profile")
def save_client_profile(client_id: int, profile: ClientProfileUpdate, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    item = db.query(ClientProfile).filter(ClientProfile.client_id == client_id, ClientProfile.tenant_id == current_user.tenant_id).first()

    if not item:
        item = ClientProfile(client_id=client_id, tenant_id=current_user.tenant_id)
        db.add(item)

    for field, value in profile.dict(exclude_unset=True).items():
        setattr(item, field, value)

    from datetime import datetime
    item.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(item)
    return item


@router.post("/{client_id}/brief/upload")
async def upload_client_brief(client_id: int, file: UploadFile = File(...), current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    import os
    import json
    from datetime import datetime
    from openpyxl import load_workbook

    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Нужен файл .xlsx")

    upload_dir = f"/root/factory/client_briefs/{client_id}"
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    wb = load_workbook(file_path, data_only=True)
    ws = wb.active

    rows = []
    headers = [cell.value for cell in ws[1]]

    for row in ws.iter_rows(min_row=2, values_only=True):
        item = {}
        for i, h in enumerate(headers):
            if h:
                item[str(h)] = row[i] if i < len(row) else None
        if any(v for v in item.values()):
            rows.append(item)

    parsed_json = json.dumps(rows, ensure_ascii=False)

    brief = ClientBriefFile(
        client_id=client_id,
        tenant_id=current_user.tenant_id,
        filename=file.filename,
        file_path=file_path,
        status="parsed",
        parsed_json=parsed_json
    )

    db.add(brief)
    db.commit()
    db.refresh(brief)

    return brief


@router.get("/{client_id}/brief/latest")
def get_latest_client_brief(client_id: int, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    return db.query(ClientBriefFile).filter(
        ClientBriefFile.client_id == client_id
    ).order_by(ClientBriefFile.created_at.desc()).first()


@router.post("/{client_id}/profile/from-brief")
def generate_profile_from_brief(client_id: int, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    import json
    from datetime import datetime

    brief = db.query(ClientBriefFile).filter(
        ClientBriefFile.client_id == client_id
    ).order_by(ClientBriefFile.created_at.desc()).first()

    if not brief or not brief.parsed_json:
        raise HTTPException(status_code=404, detail="Бриф не найден")

    rows = json.loads(brief.parsed_json)

    answers = {}
    for row in rows:
        key = row.get("Ключ системы")
        value = row.get("Ответ клиента")
        if key and value:
            answers[key] = str(value).strip()

    profile = db.query(ClientProfile).filter(ClientProfile.client_id == client_id, ClientProfile.tenant_id == current_user.tenant_id).first()

    if not profile:
        profile = ClientProfile(client_id=client_id, tenant_id=current_user.tenant_id)
        db.add(profile)

    profile.product = answers.get("product", profile.product)
    profile.target_audience = answers.get("target_audience", profile.target_audience)
    profile.tone_of_voice = answers.get("tone_of_voice", profile.tone_of_voice)
    profile.content_pillars = answers.get("content_pillars", profile.content_pillars)
    profile.usp = answers.get("usp", profile.usp)
    profile.offers = answers.get("offers", profile.offers)
    profile.competitors = answers.get("competitors", profile.competitors)
    profile.pains = answers.get("pains", profile.pains)
    profile.desires = answers.get("desires", profile.desires)
    profile.objections = answers.get("objections", profile.objections)
    profile.target_platforms = answers.get("target_platforms", profile.target_platforms)
    profile.traffic_funnel = answers.get("traffic_funnel", profile.traffic_funnel)

    # усиленный автосбор из базовых полей брифа
    company = answers.get("company_name", "")
    niche = answers.get("niche", "")
    geography = answers.get("geography", "")
    average_check = answers.get("average_check", "")

    if not profile.positioning:
        parts = []
        if company:
            parts.append(company)
        if niche:
            parts.append(f"ниша: {niche}")
        if geography:
            parts.append(f"география: {geography}")
        if average_check:
            parts.append(f"средний чек: {average_check}")
        profile.positioning = "; ".join(parts) if parts else profile.positioning

    profile.profile_status = "ready"
    profile.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(profile)
    return profile



@router.post("/{client_id}/generate-intelligence")
def generate_client_intelligence(client_id: int, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    import os
    import json
    from datetime import datetime
    import anthropic
    from dotenv import load_dotenv
    from prompt_loader import load_prompt

    load_dotenv("/root/factory/backend/.env")

    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    CLAUDE_PROXY_URL = os.getenv("CLAUDE_PROXY_URL", "http://127.0.0.1:8010")
    MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

    if not CLAUDE_API_KEY:
        raise HTTPException(status_code=500, detail="CLAUDE_API_KEY not found")

    client_obj = db.query(Client).filter(Client.id == client_id).first()
    if not client_obj:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    profile = db.query(ClientProfile).filter(ClientProfile.client_id == client_id, ClientProfile.tenant_id == current_user.tenant_id).first()
    brief = db.query(ClientBriefFile).filter(ClientBriefFile.client_id == client_id, ClientBriefFile.tenant_id == current_user.tenant_id).order_by(ClientBriefFile.created_at.desc()).first()
    channels = db.query(ClientChannel).filter(ClientChannel.client_id == client_id, ClientChannel.tenant_id == current_user.tenant_id).all()
    goals = db.query(ClientGoal).filter(ClientGoal.client_id == client_id, ClientGoal.tenant_id == current_user.tenant_id).all()
    kpis = db.query(ClientKPI).filter(ClientKPI.client_id == client_id, ClientKPI.tenant_id == current_user.tenant_id).all()
    snapshots = db.query(ClientAccountSnapshot).join(
        ClientChannel, ClientAccountSnapshot.channel_id == ClientChannel.id
    ).filter(ClientChannel.client_id == client_id, ClientChannel.tenant_id == current_user.tenant_id).order_by(ClientAccountSnapshot.created_at.desc()).all()

    input_data = {
        "client": {
            "name": client_obj.name,
            "brand": client_obj.brand,
            "niche": client_obj.niche,
            "notes": client_obj.notes,
            "status": client_obj.status,
        },
        "brief": json.loads(brief.parsed_json) if brief and brief.parsed_json else [],
        "profile": profile.__dict__ if profile else {},
        "channels": [c.__dict__ for c in channels],
        "goals": [g.__dict__ for g in goals],
        "kpis": [k.__dict__ for k in kpis],
        "account_snapshots": [s.__dict__ for s in snapshots],
    }

    for group in ["profile"]:
        if isinstance(input_data[group], dict):
            input_data[group].pop("_sa_instance_state", None)

    for group in ["channels", "goals", "kpis", "account_snapshots"]:
        for item in input_data[group]:
            item.pop("_sa_instance_state", None)

    system_prompt = load_prompt("client_intelligence_prompt.txt")

    user_prompt = (
        "Сформируй CLIENT INTELLIGENCE MAP на основе этих данных. "
        "Не копируй слабые ответы клиента дословно. Если данных не хватает — сделай профессиональные выводы. "
        "Ответ строго JSON.\n\n"
        + json.dumps(input_data, ensure_ascii=False, default=str)
    )

    ai_client = anthropic.Anthropic(
        api_key=CLAUDE_API_KEY,
        base_url=CLAUDE_PROXY_URL
    )

    try:
        msg = ai_client.messages.create(
            model=MODEL,
            max_tokens=4000,
            temperature=0.4,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Claude connection failed: {str(e)}")

    text = ""
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            text += block.text

    text = text.strip().replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(text)
    except Exception:
        print("CLAUDE RAW RESPONSE START")
        print(text[:3000])
        print("CLAUDE RAW RESPONSE END")
        raise HTTPException(status_code=500, detail="Claude вернул невалидный JSON")

    intelligence = db.query(ClientIntelligence).filter(ClientIntelligence.client_id == client_id, ClientIntelligence.tenant_id == current_user.tenant_id).first()
    if not intelligence:
        intelligence = ClientIntelligence(client_id=client_id, tenant_id=current_user.tenant_id)
        db.add(intelligence)

    def to_text(value):
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        return str(value)

    intelligence.positioning = to_text(data.get("positioning"))
    intelligence.audience_segments = to_text(data.get("audience_segments"))
    intelligence.tone_of_voice = to_text(data.get("tone_of_voice"))
    intelligence.content_pillars = to_text(data.get("content_pillars"))
    intelligence.offers = to_text(data.get("offers"))
    intelligence.usp = to_text(data.get("usp"))
    intelligence.pains = to_text(data.get("pains"))
    intelligence.desires = to_text(data.get("desires"))
    intelligence.objections = to_text(data.get("objections"))
    intelligence.customer_journey = to_text(data.get("customer_journey"))
    intelligence.traffic_funnel = to_text(data.get("traffic_funnel"))
    intelligence.content_mix = to_text(data.get("content_mix"))
    intelligence.platform_strategy = to_text(data.get("platform_strategy"))
    intelligence.growth_hypothesis = to_text(data.get("growth_hypothesis"))
    intelligence.ai_summary = to_text(data.get("ai_summary"))
    intelligence.status = "ready"
    intelligence.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(intelligence)
    return intelligence


@router.post("/{client_id}/generate-strategy")
def generate_client_strategy(client_id: int, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    import os
    import json
    from datetime import datetime
    import anthropic
    from dotenv import load_dotenv
    from prompt_loader import load_prompt
    from models import ClientStrategy

    load_dotenv("/root/factory/backend/.env")

    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    CLAUDE_PROXY_URL = os.getenv("CLAUDE_PROXY_URL", "http://127.0.0.1:8010")
    MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

    if not CLAUDE_API_KEY:
        raise HTTPException(status_code=500, detail="CLAUDE_API_KEY not found")

    client_obj = db.query(Client).filter(Client.id == client_id).first()
    if not client_obj:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    intelligence = db.query(ClientIntelligence).filter(ClientIntelligence.client_id == client_id, ClientIntelligence.tenant_id == current_user.tenant_id).first()
    profile = db.query(ClientProfile).filter(ClientProfile.client_id == client_id, ClientProfile.tenant_id == current_user.tenant_id).first()
    goals = db.query(ClientGoal).filter(ClientGoal.client_id == client_id, ClientGoal.tenant_id == current_user.tenant_id).all()
    kpis = db.query(ClientKPI).filter(ClientKPI.client_id == client_id, ClientKPI.tenant_id == current_user.tenant_id).all()
    channels = db.query(ClientChannel).filter(ClientChannel.client_id == client_id, ClientChannel.tenant_id == current_user.tenant_id).all()
    snapshots = db.query(ClientAccountSnapshot).join(
        ClientChannel, ClientAccountSnapshot.channel_id == ClientChannel.id
    ).filter(ClientChannel.client_id == client_id, ClientChannel.tenant_id == current_user.tenant_id).order_by(ClientAccountSnapshot.created_at.desc()).all()

    def clean(obj):
        if obj is None:
            return {}
        d = obj.__dict__.copy()
        d.pop("_sa_instance_state", None)
        return d

    input_data = {
        "client": {
            "name": client_obj.name,
            "brand": client_obj.brand,
            "niche": client_obj.niche,
            "notes": client_obj.notes,
        },
        "intelligence": clean(intelligence),
        "profile": clean(profile),
        "goals": [clean(g) for g in goals],
        "kpis": [clean(k) for k in kpis],
        "channels": [clean(c) for c in channels],
        "account_snapshots": [clean(s) for s in snapshots],
    }

    system_prompt = load_prompt("strategy_prompt.txt")
    user_prompt = (
        "Сформируй контент-стратегию клиента на основе этих данных. "
        "Ответ строго JSON.\n\n"
        + json.dumps(input_data, ensure_ascii=False, default=str)
    )

    ai_client = anthropic.Anthropic(
        api_key=CLAUDE_API_KEY,
        base_url=CLAUDE_PROXY_URL
    )

    try:
        msg = ai_client.messages.create(
            model=MODEL,
            max_tokens=6000,
            temperature=0.4,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Claude connection failed: {str(e)}")

    text = ""
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            text += block.text

    text = text.strip().replace("```json", "").replace("```", "").strip()

    # Защита от обрезанного JSON
    if not text.endswith("}"):
        last = text.rfind("}")
        if last != -1:
            text = text[:last+1]

    try:
        data = json.loads(text)
    except Exception:
        print("STRATEGY RAW:", text[:3000])
        raise HTTPException(status_code=500, detail="Claude strategy JSON error")

    def to_text(value):
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        return str(value)

    strategy = db.query(ClientStrategy).filter(ClientStrategy.client_id == client_id, ClientStrategy.tenant_id == current_user.tenant_id).first()
    if not strategy:
        strategy = ClientStrategy(client_id=client_id, tenant_id=current_user.tenant_id)
        db.add(strategy)

    strategy.positioning = to_text(data.get("positioning"))
    strategy.content_pillars = to_text(data.get("content_pillars"))
    strategy.platform_strategy = to_text(data.get("platform_strategy"))
    strategy.funnel = to_text(data.get("funnel"))
    strategy.content_mix = to_text(data.get("content_mix"))
    strategy.posting_frequency = to_text(data.get("posting_frequency"))
    strategy.growth_hypotheses = to_text(data.get("growth_hypotheses"))
    strategy.action_plan_30 = to_text(data.get("action_plan_30"))
    strategy.risks = to_text(data.get("risks"))
    strategy.kpi_targets = to_text(data.get("kpi_targets"))
    strategy.ai_summary = to_text(data.get("ai_summary"))
    strategy.status = "ready"
    strategy.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(strategy)

    log_event(
        db=db,
        action="STRATEGY_GENERATE",
        user=current_user,
        entity_type="client_strategy",
        entity_id=strategy.id,
    )

    return strategy


@router.get("/{client_id}/content-plan/latest")
def get_latest_content_plan(client_id: int, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    from models import ClientContentPlan
    plan = db.query(ClientContentPlan).filter(
        ClientContentPlan.client_id == client_id
    ).order_by(ClientContentPlan.created_at.desc()).first()
    if not plan:
        return None
    return plan


@router.post("/{client_id}/generate-content-plan")
def generate_content_plan(client_id: int, current_user: User = Depends(require_roles("SUPER_ADMIN", "ADMIN", "MANAGER")), db: Session = Depends(get_db)):
    client = get_tenant_client(client_id, current_user, db)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    import os
    import json
    from datetime import datetime
    import anthropic
    from dotenv import load_dotenv
    from prompt_loader import load_prompt
    from models import ClientContentPlan

    load_dotenv("/root/factory/backend/.env")

    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    CLAUDE_PROXY_URL = os.getenv("CLAUDE_PROXY_URL", "http://127.0.0.1:8010")
    MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

    if not CLAUDE_API_KEY:
        raise HTTPException(status_code=500, detail="CLAUDE_API_KEY not found")

    client_obj = db.query(Client).filter(Client.id == client_id).first()
    if not client_obj:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    strategy = db.query(ClientStrategy).filter(ClientStrategy.client_id == client_id, ClientStrategy.tenant_id == current_user.tenant_id).first()
    intelligence = db.query(ClientIntelligence).filter(ClientIntelligence.client_id == client_id, ClientIntelligence.tenant_id == current_user.tenant_id).first()
    profile = db.query(ClientProfile).filter(ClientProfile.client_id == client_id, ClientProfile.tenant_id == current_user.tenant_id).first()
    goals = db.query(ClientGoal).filter(ClientGoal.client_id == client_id, ClientGoal.tenant_id == current_user.tenant_id).all()
    kpis = db.query(ClientKPI).filter(ClientKPI.client_id == client_id, ClientKPI.tenant_id == current_user.tenant_id).all()
    channels = db.query(ClientChannel).filter(ClientChannel.client_id == client_id, ClientChannel.tenant_id == current_user.tenant_id).all()

    def clean(obj):
        if obj is None:
            return {}
        d = obj.__dict__.copy()
        d.pop("_sa_instance_state", None)
        return d

    now = datetime.utcnow()
    input_data = {
        "client": {"name": client_obj.name, "brand": client_obj.brand, "niche": client_obj.niche},
        "month": now.strftime("%B %Y"),
        "strategy": clean(strategy),
        "intelligence": clean(intelligence),
        "profile": clean(profile),
        "goals": [clean(g) for g in goals],
        "kpis": [clean(k) for k in kpis],
        "channels": [clean(c) for c in channels],
    }

    system_prompt = load_prompt("content_plan_prompt.txt")
    user_prompt = (
        f"Составь контент-план на первые 2 недели (15 постов максимум) для {now.strftime('%B %Y')} для клиента. "
        "Ответ строго JSON.\n\n"
        + json.dumps(input_data, ensure_ascii=False, default=str)
    )

    ai_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY, base_url=CLAUDE_PROXY_URL)

    try:
        msg = ai_client.messages.create(
            model=MODEL,
            max_tokens=6000,
            temperature=0.4,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Claude connection failed: {str(e)}")

    text = ""
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            text += block.text

    text = text.strip().replace("```json", "").replace("```", "").strip()

    if not text.endswith("}"):
        last = text.rfind("}")
        if last != -1:
            text = text[:last+1]

    try:
        data = json.loads(text)
    except Exception:
        print("CONTENT PLAN RAW:", text[:3000])
        raise HTTPException(status_code=500, detail="Claude content plan JSON error")

    plan = ClientContentPlan(
        client_id=client_id,
        tenant_id=current_user.tenant_id,
        month=now.strftime("%B"),
        year=now.year,
        platform_focus=json.dumps(data.get("platform_focus", []), ensure_ascii=False),
        posts_json=json.dumps(data.get("posts", []), ensure_ascii=False),
        summary=json.dumps({
            "month_summary": data.get("month_summary"),
            "weekly_breakdown": data.get("weekly_breakdown"),
            "ai_summary": data.get("ai_summary"),
            "total_posts": data.get("total_posts"),
        }, ensure_ascii=False),
        status="ready"
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    log_event(
        db=db,
        action="CONTENT_PLAN_GENERATE",
        user=current_user,
        entity_type="client_content_plan",
        entity_id=plan.id,
    )

    return plan
