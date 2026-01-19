from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
import secrets
from datetime import datetime, timedelta

from ..db import get_db
from ..models import Guest, Profile, FamilyGroup, InviteToken
from ..config import settings
from ..services.telegram_auth import verify_telegram_init_data
from ..schemas import FamilyAcceptIn, FamilyInviteOut, FamilyStatusOut

router = APIRouter(prefix="/api/family", tags=["family"])


def _guest_from_initdata(initdata: str, db: Session) -> Guest:
    user = verify_telegram_init_data(initdata, settings.BOT_TOKEN)
    tg_id = int(user["id"])
    guest = db.query(Guest).filter(Guest.telegram_user_id == tg_id).one_or_none()
    if not guest:
        guest = Guest(
            telegram_user_id=tg_id,
            username=user.get("username"),
            first_name=user.get("first_name"),
            last_name=user.get("last_name"),
        )
        db.add(guest)
        db.flush()
        db.add(Profile(guest_id=guest.id))
        db.commit()
        db.refresh(guest)
    return guest


def _guest_from_internal(telegram_user_id: int, db: Session) -> Guest:
    guest = db.query(Guest).filter(Guest.telegram_user_id == telegram_user_id).one_or_none()
    if not guest:
        guest = Guest(telegram_user_id=telegram_user_id)
        db.add(guest)
        db.flush()
        db.add(Profile(guest_id=guest.id))
        db.commit()
        db.refresh(guest)
    return guest


@router.post("/invite", response_model=FamilyInviteOut)
def invite_family(
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    telegram_user_id: int | None = None,
    db: Session = Depends(get_db),
):
    if x_internal_secret == settings.INTERNAL_SECRET and telegram_user_id:
        guest = _guest_from_internal(telegram_user_id, db)
    elif x_tg_initdata:
        guest = _guest_from_initdata(x_tg_initdata, db)
    else:
        raise HTTPException(401, "Missing auth")

    if guest.family_group_id is None:
        group = FamilyGroup()
        db.add(group)
        db.flush()
        guest.family_group_id = group.id
        db.add(guest)
        db.commit()

    token = secrets.token_urlsafe(16)
    invite = InviteToken(
        token=token,
        family_group_id=guest.family_group_id,
        inviter_guest_id=guest.id,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invite)
    db.commit()
    return FamilyInviteOut(token=token)


@router.post("/accept")
def accept_invite(
    body: FamilyAcceptIn,
    x_tg_initdata: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    telegram_user_id: int | None = None,
    db: Session = Depends(get_db),
):
    if x_internal_secret == settings.INTERNAL_SECRET and telegram_user_id:
        guest = _guest_from_internal(telegram_user_id, db)
    elif x_tg_initdata:
        guest = _guest_from_initdata(x_tg_initdata, db)
    else:
        raise HTTPException(401, "Missing auth")

    invite = db.query(InviteToken).filter(InviteToken.token == body.token).one_or_none()
    if not invite:
        raise HTTPException(404, "Invite not found")
    if invite.used_by_guest_id:
        raise HTTPException(400, "Invite already used")
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        raise HTTPException(400, "Invite expired")

    guest.family_group_id = invite.family_group_id
    invite.used_by_guest_id = guest.id
    db.add(guest)
    db.add(invite)
    db.commit()
    return {"ok": True, "family_group_id": guest.family_group_id}


@router.get("/status", response_model=FamilyStatusOut)
def family_status(x_tg_initdata: str = Header(...), db: Session = Depends(get_db)):
    guest = _guest_from_initdata(x_tg_initdata, db)
    if not guest.family_group_id:
        return FamilyStatusOut(family_group_id=None, members=[])

    members = db.query(Guest, Profile).join(Profile, Profile.guest_id == Guest.id).filter(
        Guest.family_group_id == guest.family_group_id
    ).all()
    out = []
    for g, p in members:
        name = p.full_name or f"{g.first_name or ''} {g.last_name or ''}".strip()
        out.append({
            "guest_id": g.id,
            "telegram_user_id": g.telegram_user_id,
            "name": name,
            "rsvp": p.rsvp_status,
        })
    return FamilyStatusOut(family_group_id=guest.family_group_id, members=out)
