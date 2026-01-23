from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
import os

from ..db import get_db, engine
from ..models import Guest, Profile, EventInfo, Group, GroupMember, FamilyGroup, InviteToken, ChangeLog, FamilyProfile, AdminSettings
from ..schemas import AdminEventInfoIn, BroadcastIn
from ..config import settings
from ..services.telegram_auth import verify_telegram_init_data
from ..services.notifier import notify_admins, send_admin_message

router = APIRouter(prefix="/api/admin", tags=["admin"])

def _assert_admin_or_internal(initdata: str | None, internal: str | None):
    if internal and internal == settings.INTERNAL_SECRET:
        return
    if not initdata:
        raise HTTPException(401, "Missing initData")
    user = verify_telegram_init_data(initdata, settings.BOT_TOKEN)
    if int(user["id"]) not in settings.admin_id_set:
        raise HTTPException(403, "Admin only")

@router.get("/guests")
def list_guests(
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    rsvp: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    _assert_admin_or_internal(x_tg_initdata, x_internal_secret)
    query = db.query(Guest, Profile, FamilyProfile).join(Profile, Profile.guest_id == Guest.id).outerjoin(
        FamilyProfile, FamilyProfile.guest_id == Guest.id
    )
    if rsvp:
        query = query.filter(Profile.rsvp_status == rsvp)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (Profile.full_name.ilike(like)) |
            (Guest.username.ilike(like)) |
            (Guest.phone.ilike(like))
        )
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    out = []
    for g, p, fp in rows:
        alcohol = p.alcohol_prefs_csv or ""
        children_count = 0
        if fp and fp.children_json:
            try:
                import json as _json
                children_count = len(_json.loads(fp.children_json))
            except Exception:
                children_count = 0
        out.append({
            "guest_id": g.id,
            "telegram_user_id": g.telegram_user_id,
            "name": p.full_name or f"{g.first_name or ''} {g.last_name or ''}".strip(),
            "username": g.username,
            "rsvp": p.rsvp_status,
            "side": p.side,
            "relative": p.is_relative,
            "food": p.food_pref,
            "allergies": p.food_allergies,
            "gender": p.gender,
            "alcohol": alcohol,
            "phone": g.phone,
            "family_group_id": g.family_group_id,
            "children_count": children_count,
            "updated_at": g.updated_at.isoformat() if g.updated_at else None,
        })
    return {"items": out, "total": total, "page": page, "page_size": page_size}

@router.get("/event")
def get_event_info(
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _assert_admin_or_internal(x_tg_initdata, x_internal_secret)
    row = db.query(EventInfo).first()
    if not row:
        row = EventInfo(content="Заглушка: здесь будет общая информация о мероприятии.")
        db.add(row)
        db.commit()
        db.refresh(row)
    return {"content": row.content, "updated_at": row.updated_at.isoformat()}

@router.post("/event")
async def update_event_info(
    body: AdminEventInfoIn,
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _assert_admin_or_internal(x_tg_initdata, x_internal_secret)
    row = db.query(EventInfo).first()
    if not row:
        row = EventInfo(content=body.content)
        db.add(row)
    else:
        row.content = body.content
    db.commit()
    try:
        await send_admin_message(
            f"<b>Информация о мероприятии обновлена</b>\nДлина: {len(body.content)}",
            category="system",
            db=db,
        )
    except Exception:
        pass
    return {"ok": True}

@router.post("/broadcast")
async def broadcast(
    body: BroadcastIn,
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _assert_admin_or_internal(x_tg_initdata, x_internal_secret)
    # backend only forwards request to bot; bot resolves recipients by group_ids
    await notify_admins("broadcast", {"text": body.text, "group_ids": body.group_ids})
    return {"ok": True}

@router.delete("/guest/{guest_id}")
def delete_guest(
    guest_id: int,
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _assert_admin_or_internal(x_tg_initdata, x_internal_secret)
    guest = db.query(Guest).filter(Guest.id == guest_id).one_or_none()
    if not guest:
        raise HTTPException(404, "Guest not found")
    db.delete(guest)
    db.commit()
    return {"ok": True}

@router.post("/clear-db")
def clear_db(
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _assert_admin_or_internal(x_tg_initdata, x_internal_secret)
    counts = {
        "guests": db.query(Guest).count(),
        "profiles": db.query(Profile).count(),
        "groups": db.query(Group).count(),
        "group_members": db.query(GroupMember).count(),
        "family_groups": db.query(FamilyGroup).count(),
        "invite_tokens": db.query(InviteToken).count(),
        "family_profiles": db.query(FamilyProfile).count(),
        "change_log": db.query(ChangeLog).count(),
    }
    db.query(ChangeLog).delete()
    db.query(InviteToken).delete()
    db.query(GroupMember).delete()
    db.query(Group).delete()
    db.query(FamilyProfile).delete()
    db.query(Profile).delete()
    db.query(Guest).delete()
    db.query(FamilyGroup).delete()
    db.commit()
    return counts

@router.get("/notification-settings")
def get_notification_settings(
    admin_id: int = Query(..., ge=1),
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not x_internal_secret or x_internal_secret != settings.INTERNAL_SECRET:
        raise HTTPException(403, "Forbidden")
    row = db.query(AdminSettings).filter(AdminSettings.admin_id == admin_id).one_or_none()
    enabled = True if not row else bool(row.system_notifications_enabled)
    return {"admin_id": admin_id, "system_notifications_enabled": enabled}

@router.post("/notification-settings")
def set_notification_settings(
    body: dict,
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not x_internal_secret or x_internal_secret != settings.INTERNAL_SECRET:
        raise HTTPException(403, "Forbidden")
    admin_id = int(body.get("admin_id") or 0)
    enabled = bool(body.get("system_notifications_enabled", True))
    if admin_id <= 0:
        raise HTTPException(400, "Missing admin_id")
    row = db.query(AdminSettings).filter(AdminSettings.admin_id == admin_id).one_or_none()
    if not row:
        row = AdminSettings(admin_id=admin_id, system_notifications_enabled=enabled)
        db.add(row)
    else:
        row.system_notifications_enabled = enabled
        db.add(row)
    db.commit()
    return {"admin_id": admin_id, "system_notifications_enabled": enabled}

@router.get("/db-health")
def db_health(
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _assert_admin_or_internal(x_tg_initdata, x_internal_secret)
    db_path = engine.url.database or ""
    if db_path and not os.path.isabs(db_path):
        db_path = os.path.abspath(os.path.join(os.getcwd(), db_path))
    exists = os.path.exists(db_path) if db_path else False
    size_bytes = os.path.getsize(db_path) if exists else 0
    with engine.begin() as conn:
        tables = [r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))]
    counts = {
        "guests": db.query(Guest).count(),
        "profiles": db.query(Profile).count(),
        "family_groups": db.query(FamilyGroup).count(),
        "invite_tokens": db.query(InviteToken).count(),
        "family_profiles": db.query(FamilyProfile).count(),
    }
    return {
        "path": db_path,
        "exists": exists,
        "size_bytes": size_bytes,
        "tables": tables,
        "counts": counts,
    }
