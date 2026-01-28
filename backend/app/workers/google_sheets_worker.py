import time
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import SheetSyncJob, Guest, Profile, FamilyProfile
from ..services.google_sheets import _get_service, ensure_formatting, upsert_row, to_row

logger = logging.getLogger(__name__)

POLL_SECONDS = 5
MAX_ATTEMPTS = 5

def _children_string(fp: FamilyProfile | None) -> str:
    if not fp or not fp.children_json:
        return ""
    try:
        import json as _json
        items = _json.loads(fp.children_json)
        out = []
        for ch in items:
            name = (ch.get("name") or "").strip()
            age = (ch.get("age") or "").strip()
            if name and age:
                out.append(f"{name} ({age})")
            elif name:
                out.append(name)
        return ", ".join(out)
    except Exception:
        return ""

def _load_guest(db: Session, telegram_id: int) -> dict | None:
    g = db.query(Guest).filter(Guest.telegram_user_id == telegram_id).one_or_none()
    if not g:
        return None
    p = g.profile
    fp = db.query(FamilyProfile).filter(FamilyProfile.guest_id == g.id).one_or_none()
    alcohol = (p.alcohol_prefs_csv or "").strip()
    return {
        "telegram_id": g.telegram_user_id,
        "tg_username": g.username or "",
        "full_name": p.full_name or "",
        "phone": g.phone or "",
        "gender": p.gender or "",
        "side": p.side or "",
        "attendance_status": p.rsvp_status or "",
        "is_relative": bool(p.is_relative),
        "is_best_friend": bool(getattr(p, "is_best_friend", False)),
        "has_plus_one_requested": bool(getattr(p, "has_plus_one_requested", False)),
        "plus_one_partner_username": getattr(p, "plus_one_partner_username", None) or "",
        "children": _children_string(fp),
        "allergies": p.food_allergies or "",
        "food": p.food_pref or "",
        "alcohol": alcohol,
        "updated_at": g.updated_at.isoformat() if g.updated_at else "",
        "created_at": g.created_at.isoformat() if g.created_at else "",
    }

def _process_job(db: Session, job: SheetSyncJob) -> None:
    service = _get_service()
    ensure_formatting(service)
    if job.type == "sync_all":
        guests = db.query(Guest).all()
        for g in guests:
            data = _load_guest(db, g.telegram_user_id)
            if data:
                upsert_row(service, to_row(data))
        return
    if job.telegram_id:
        data = _load_guest(db, job.telegram_id)
        if data:
            upsert_row(service, to_row(data))

def main():
    logger.info("Google Sheets worker started")
    while True:
        db = SessionLocal()
        try:
            job = (
                db.query(SheetSyncJob)
                .filter(SheetSyncJob.status == "pending")
                .order_by(SheetSyncJob.created_at.asc())
                .first()
            )
            if not job:
                db.close()
                time.sleep(POLL_SECONDS)
                continue
            job.status = "processing"
            job.updated_at = datetime.utcnow()
            db.add(job)
            db.commit()
            try:
                _process_job(db, job)
                job.status = "done"
                job.updated_at = datetime.utcnow()
                db.add(job)
                db.commit()
            except Exception as e:
                job.attempts = (job.attempts or 0) + 1
                job.status = "pending" if job.attempts < MAX_ATTEMPTS else "failed"
                job.updated_at = datetime.utcnow()
                db.add(job)
                db.commit()
                logger.warning("sheets job failed (id=%s, attempts=%s): %s", job.id, job.attempts, str(e))
                time.sleep(min(30, POLL_SECONDS * (job.attempts + 1)))
        finally:
            db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
