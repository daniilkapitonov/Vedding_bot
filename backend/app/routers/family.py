from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
import secrets
from datetime import datetime, timedelta
import json

from ..db import get_db
from ..models import Guest, Profile, FamilyGroup, InviteToken, FamilyProfile
from ..config import settings
from ..services.telegram_auth import verify_telegram_init_data, get_guest_from_invite
from ..schemas import FamilyAcceptIn, FamilyInviteOut, FamilyStatusOut, FamilySaveIn, FamilyOut, FamilyInviteByNameIn
from ..services.notifier import send_admin_message

router = APIRouter(prefix="/api/family", tags=["family"])


def _guest_from_initdata(initdata: str | None, invite_token: str | None, db: Session) -> Guest:
    if not initdata and invite_token:
        return get_guest_from_invite(invite_token, db)
    user = verify_telegram_init_data(initdata or "", settings.BOT_TOKEN)
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
    x_invite_token: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    telegram_user_id: int | None = None,
    db: Session = Depends(get_db),
):
    if x_internal_secret == settings.INTERNAL_SECRET and telegram_user_id:
        guest = _guest_from_internal(telegram_user_id, db)
    elif x_tg_initdata or x_invite_token:
        guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
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
    x_invite_token: str | None = Header(default=None),
    x_internal_secret: str | None = Header(default=None),
    telegram_user_id: int | None = None,
    db: Session = Depends(get_db),
):
    if x_internal_secret == settings.INTERNAL_SECRET and telegram_user_id:
        guest = _guest_from_internal(telegram_user_id, db)
    elif x_tg_initdata or x_invite_token:
        guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
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
def family_status(
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
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

@router.get("/me", response_model=FamilyOut)
def get_family(
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    row = db.query(FamilyProfile).filter(FamilyProfile.guest_id == guest.id).one_or_none()
    if not row:
        return FamilyOut(with_partner=False, partner_name=None, children=[])
    children = []
    if row.children_json:
        try:
            children = json.loads(row.children_json)
        except Exception:
            children = []
    return FamilyOut(with_partner=row.with_partner, partner_name=row.partner_name, children=children)

@router.post("/save", response_model=FamilyOut)
async def save_family(
    body: FamilySaveIn,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    row = db.query(FamilyProfile).filter(FamilyProfile.guest_id == guest.id).one_or_none()
    before = {
        "with_partner": bool(row.with_partner) if row else False,
        "partner_name": row.partner_name if row else None,
        "children_count": len(json.loads(row.children_json)) if row and row.children_json else 0,
    }
    children_json = json.dumps(body.children or [])
    if not row:
        row = FamilyProfile(
            guest_id=guest.id,
            with_partner=body.with_partner,
            partner_name=body.partner_name,
            children_json=children_json,
        )
        db.add(row)
    else:
        row.with_partner = body.with_partner
        row.partner_name = body.partner_name
        row.children_json = children_json
        db.add(row)
    db.commit()
    after = {
        "with_partner": bool(row.with_partner),
        "partner_name": row.partner_name,
        "children_count": len(body.children or []),
    }
    changes = []
    if before["with_partner"] != after["with_partner"]:
        changes.append(("Пара", "Да" if before["with_partner"] else "Нет", "Да" if after["with_partner"] else "Нет"))
    if before["partner_name"] != after["partner_name"]:
        changes.append(("Партнёр", before["partner_name"] or "—", after["partner_name"] or "—"))
    if before["children_count"] != after["children_count"]:
        changes.append(("Дети (кол-во)", str(before["children_count"]), str(after["children_count"])))
    if changes:
        try:
            name = guest.profile.full_name if guest.profile else ""
            if not name:
                name = f"{guest.first_name or ''} {guest.last_name or ''}".strip() or "Гость"
            lines = [f"<b>Семья обновлена</b>", f"{name} (id {guest.id})", ""]
            for label, old, new in changes:
                lines.append(f"{label}: {old} → {new}")
            await send_admin_message("\n".join(lines), category="system", db=db)
        except Exception:
            pass
    return FamilyOut(with_partner=row.with_partner, partner_name=row.partner_name, children=body.children or [])

@router.post("/invite-by-name")
def invite_by_name(
    body: FamilyInviteByNameIn,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    full_name = (body.full_name or "").strip()
    if not full_name:
        raise HTTPException(400, "Missing full_name")

    candidate = (
        db.query(Profile)
        .filter(Profile.full_name.ilike(full_name))
        .one_or_none()
    )
    if not candidate:
        raise HTTPException(404, "Guest not found")

    if guest.family_group_id is None:
        group = FamilyGroup()
        db.add(group)
        db.flush()
        guest.family_group_id = group.id
        db.add(guest)
        db.commit()

    other = db.query(Guest).filter(Guest.id == candidate.guest_id).one_or_none()
    if other and other.family_group_id != guest.family_group_id:
        other.family_group_id = guest.family_group_id
        db.add(other)
        db.commit()

    return {"ok": True, "family_group_id": guest.family_group_id}

@router.get("/invite/{token}")
def invite_info(token: str, db: Session = Depends(get_db)):
    invite = db.query(InviteToken).filter(InviteToken.token == token).one_or_none()
    if not invite:
        raise HTTPException(404, "Invite not found")
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        raise HTTPException(400, "Invite expired")
    inviter = db.query(Guest).filter(Guest.id == invite.inviter_guest_id).one_or_none()
    name = None
    if inviter:
        profile = db.query(Profile).filter(Profile.guest_id == inviter.id).one_or_none()
        if profile and profile.full_name:
            name = profile.full_name
    return {
        "token": invite.token,
        "family_group_id": invite.family_group_id,
        "inviter_name": name,
        "used": bool(invite.used_by_guest_id),
    }
