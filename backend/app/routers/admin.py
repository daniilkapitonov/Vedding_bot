from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Guest, Profile, EventInfo, Group, GroupMember, FamilyGroup, InviteToken, ChangeLog
from ..schemas import AdminEventInfoIn, BroadcastIn
from ..config import settings
from ..services.telegram_auth import verify_telegram_init_data
from ..services.notifier import notify_admins

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
    query = db.query(Guest, Profile).join(Profile, Profile.guest_id == Guest.id)
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
    for g, p in rows:
        out.append({
            "guest_id": g.id,
            "telegram_user_id": g.telegram_user_id,
            "name": p.full_name or f"{g.first_name or ''} {g.last_name or ''}".strip(),
            "rsvp": p.rsvp_status,
            "side": p.side,
            "relative": p.is_relative,
            "food": p.food_pref,
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
    await notify_admins("event_info_updated", {"len": len(body.content)})
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
        "change_log": db.query(ChangeLog).count(),
    }
    with db.begin():
        db.query(ChangeLog).delete()
        db.query(InviteToken).delete()
        db.query(GroupMember).delete()
        db.query(Group).delete()
        db.query(Profile).delete()
        db.query(Guest).delete()
        db.query(FamilyGroup).delete()
    return counts
