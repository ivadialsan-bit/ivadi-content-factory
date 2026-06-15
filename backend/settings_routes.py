from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import UserProfile
from datetime import datetime

router = APIRouter(prefix="/api/settings")

@router.get("/profile")
def get_profile(db: Session = Depends(get_db)):
    p = db.query(UserProfile).first()
    if not p:
        return {"id": None, "skills": "", "niches": "", "rates": "", "cases": "", "about": ""}
    return {
        "id": p.id,
        "skills": p.skills or "",
        "niches": p.niches or "",
        "rates": p.rates or "",
        "cases": p.cases or "",
        "about": p.about or "",
        "updated_at": str(p.updated_at)
    }

@router.post("/profile")
def save_profile(data: dict, db: Session = Depends(get_db)):
    p = db.query(UserProfile).first()
    if not p:
        p = UserProfile()
        db.add(p)
    p.skills = data.get("skills", "")
    p.niches = data.get("niches", "")
    p.rates = data.get("rates", "")
    p.cases = data.get("cases", "")
    p.about = data.get("about", "")
    p.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(p)
    return {"ok": True, "id": p.id}
