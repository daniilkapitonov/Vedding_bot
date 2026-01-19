from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Guest, Profile, EventInfo, Group, GroupMember
from ..schemas import AdminEventInfoIn, BroadcastIn
from ..config import settings
from ..services.telegram_auth import verify_telegram_init_data
from ..services.notifier import notify_admins

router = APIRouter(prefix="/api/admin", tags=["admin"])

def _assert_admin(initdata: str):
    user = verify_telegram_init_data(initdata, settings.BOT_TOKEN)
    if int(user["id"]) not in settings.admin_id_set:
        raise HTTPException(403, "Admin only")

@router.get("/guests")
def list_guests(x_tg_initdata: str = Header(...), db: Session = Depends(get_db)):
    _assert_admin(x_tg_initdata)
    rows = db.query(Guest, Profile).join(Profile, Profile.guest_id == Guest.id).all()
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
    return out

@router.post("/event")
async def update_event_info(body: AdminEventInfoIn, x_tg_initdata: str = Header(...), db: Session = Depends(get_db)):
    _assert_admin(x_tg_initdata)
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
async def broadcast(body: BroadcastIn, x_tg_initdata: str = Header(...), db: Session = Depends(get_db)):
    _assert_admin(x_tg_initdata)
    # backend only forwards request to bot; bot resolves recipients by group_ids
    await notify_admins("broadcast", {"text": body.text, "group_ids": body.group_ids})
    return {"ok": True}
