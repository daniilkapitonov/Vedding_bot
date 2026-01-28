from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import os

from ..db import get_db, engine
from ..models import Guest, Profile, EventInfo, Group, GroupMember, FamilyGroup, InviteToken, ChangeLog, FamilyProfile, AdminSettings, AppSettings, EventContent, EventTiming
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
    family_counts = {}
    rows_counts = (
        db.query(Guest.family_group_id, func.count(Guest.id))
        .filter(Guest.family_group_id.isnot(None))
        .group_by(Guest.family_group_id)
        .all()
    )
    for fg_id, cnt in rows_counts:
        family_counts[int(fg_id)] = int(cnt)
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
            "family_members_count": family_counts.get(g.family_group_id or 0, 0) if g.family_group_id else 0,
            "children_count": children_count,
            "best_friend": bool(getattr(p, "is_best_friend", False)),
            "updated_at": g.updated_at.isoformat() if g.updated_at else None,
        })
    return {"items": out, "total": total, "page": page, "page_size": page_size}

def _event_content_get(db: Session, key: str, default: str) -> str:
    row = db.query(EventContent).filter(EventContent.key == key).one_or_none()
    if not row:
        row = EventContent(key=key, value_text=default)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row.value_text

def _event_content_set(db: Session, key: str, value: str) -> None:
    row = db.query(EventContent).filter(EventContent.key == key).one_or_none()
    if not row:
        row = EventContent(key=key, value_text=value)
        db.add(row)
    else:
        row.value_text = value
        db.add(row)
    db.commit()

@router.get("/event-content")
def get_event_content_admin(
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _assert_admin_or_internal(x_tg_initdata, x_internal_secret)
    from .event_info import DEFAULT_EVENT_CONTENT
    data = {}
    for key, default_text in DEFAULT_EVENT_CONTENT.items():
        data[key] = _event_content_get(db, key, default_text)
    return data

@router.post("/event-content")
def set_event_content_admin(
    body: dict,
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _assert_admin_or_internal(x_tg_initdata, x_internal_secret)
    key = (body.get("key") or "").strip()
    value = body.get("value_text") or ""
    if not key:
        raise HTTPException(400, "Missing key")
    _event_content_set(db, key, value)
    return {"ok": True, "key": key}

def _set_timing(db: Session, group: int, items: list[dict]) -> None:
    import json as _json
    row = db.query(EventTiming).filter(EventTiming.group == group).one_or_none()
    if not row:
        row = EventTiming(group=group, value_json=_json.dumps(items, ensure_ascii=False))
        db.add(row)
    else:
        row.value_json = _json.dumps(items, ensure_ascii=False)
        db.add(row)
    db.commit()

def _get_timing(db: Session, group: int) -> list[dict]:
    import json as _json
    row = db.query(EventTiming).filter(EventTiming.group == group).one_or_none()
    if not row:
        return []
    try:
        return _json.loads(row.value_json or "[]")
    except Exception:
        return []

@router.get("/event-timing")
def get_event_timing_admin(
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _assert_admin_or_internal(x_tg_initdata, x_internal_secret)
    return {
        "group1": _get_timing(db, 1),
        "group2": _get_timing(db, 2),
    }

@router.post("/event-timing")
def set_event_timing_admin(
    body: dict,
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _assert_admin_or_internal(x_tg_initdata, x_internal_secret)
    group = int(body.get("group") or 0)
    items = body.get("items") or []
    if group not in (1, 2):
        raise HTTPException(400, "Invalid group")
    _set_timing(db, group, items)
    return {"ok": True, "group": group, "count": len(items)}

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
    enabled = False if not row else bool(row.system_notifications_enabled)
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

def _get_app_setting(db: Session, key: str, default: bool) -> bool:
    row = db.query(AppSettings).filter(AppSettings.key == key).one_or_none()
    if not row:
        return default
    return row.value.lower() == "true"

def _set_app_setting(db: Session, key: str, value: bool) -> None:
    row = db.query(AppSettings).filter(AppSettings.key == key).one_or_none()
    if not row:
        row = AppSettings(key=key, value="true" if value else "false")
        db.add(row)
    else:
        row.value = "true" if value else "false"
        db.add(row)
    db.commit()

@router.get("/ui-settings")
def get_ui_settings_admin(
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _assert_admin_or_internal(x_tg_initdata, x_internal_secret)
    return {
        "ui_animations_enabled": _get_app_setting(db, "ui_animations_enabled", True),
        "welcome_tooltip_enabled": _get_app_setting(db, "welcome_tooltip_enabled", True),
    }

@router.post("/ui-settings")
def set_ui_settings_admin(
    body: dict,
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _assert_admin_or_internal(x_tg_initdata, x_internal_secret)
    if "ui_animations_enabled" in body:
        _set_app_setting(db, "ui_animations_enabled", bool(body.get("ui_animations_enabled")))
    if "welcome_tooltip_enabled" in body:
        _set_app_setting(db, "welcome_tooltip_enabled", bool(body.get("welcome_tooltip_enabled")))
    return {
        "ui_animations_enabled": _get_app_setting(db, "ui_animations_enabled", True),
        "welcome_tooltip_enabled": _get_app_setting(db, "welcome_tooltip_enabled", True),
    }

@router.get("/ui-settings-public")
def get_ui_settings_public(db: Session = Depends(get_db)):
    return {
        "ui_animations_enabled": _get_app_setting(db, "ui_animations_enabled", True),
        "welcome_tooltip_enabled": _get_app_setting(db, "welcome_tooltip_enabled", True),
    }

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
