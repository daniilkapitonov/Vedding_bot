from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
import secrets
from datetime import datetime, timedelta
import json
import logging
import httpx

from ..db import get_db
from ..models import Guest, Profile, FamilyGroup, InviteToken, FamilyProfile
from ..config import settings
from ..services.telegram_auth import verify_telegram_init_data, get_guest_from_invite
from ..schemas import FamilyAcceptIn, FamilyInviteOut, FamilyStatusOut, FamilySaveIn, FamilyOut, FamilyInviteByUsernameIn, FamilyCheckUsernameIn, FamilyIncomingInviteOut, FamilyRemovePartnerIn
from ..services.notifier import send_admin_message, send_user_message

router = APIRouter(prefix="/api/family", tags=["family"])
logger = logging.getLogger(__name__)


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
    else:
        member_count = db.query(Guest).filter(Guest.family_group_id == guest.family_group_id).count()
        if member_count >= 2:
            raise HTTPException(409, "Family already has 2 adults")

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
            "username": g.username,
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

def _normalize_child_contact(value: str | None) -> str:
    if not value:
        return ""
    v = value.strip().lower()
    if v.startswith("https://t.me/"):
        v = v.replace("https://t.me/", "", 1)
    if v.startswith("http://t.me/"):
        v = v.replace("http://t.me/", "", 1)
    if v.startswith("t.me/"):
        v = v.replace("t.me/", "", 1)
    return v.lstrip("@")

async def _resolve_username(username: str) -> tuple[str | None, int | None]:
    if not settings.BOT_TOKEN or not username:
        return None, None
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/getChat"
    async with httpx.AsyncClient(timeout=6) as client:
        try:
            resp = await client.get(url, params={"chat_id": f"@{username}"})
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if not data.get("ok"):
                return None, None
            result = data.get("result") or {}
            return result.get("username") or username, result.get("id")
        except Exception as e:
            logger.warning("resolve username failed: %s", str(e))
            return None, None

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
    children_input = body.children or []
    normalized_children = []
    for child in children_input:
        if not isinstance(child, dict):
            continue
        contact = _normalize_child_contact(child.get("child_contact") or child.get("contact"))
        username = None
        user_id = None
        if contact:
            username, user_id = await _resolve_username(contact)
            if user_id:
                try:
                    await send_user_message(
                        user_id,
                        "Вас добавили в семейную группу приглашения на свадьбу. Подтверждение не требуется."
                    )
                except Exception:
                    pass
        normalized_child = {
            "id": child.get("id"),
            "name": child.get("name"),
            "age": child.get("age"),
            "note": child.get("note"),
            "child_contact": contact or None,
            "child_telegram_username": username or None,
            "child_telegram_user_id": user_id,
        }
        normalized_children.append(normalized_child)
    children_json = json.dumps(normalized_children)
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
    return FamilyOut(with_partner=row.with_partner, partner_name=row.partner_name, children=normalized_children)

def _normalize_username(username: str) -> str:
    value = (username or "").strip().lower()
    if value.startswith("https://t.me/"):
        value = value.replace("https://t.me/", "", 1)
    if value.startswith("http://t.me/"):
        value = value.replace("http://t.me/", "", 1)
    if value.startswith("t.me/"):
        value = value.replace("t.me/", "", 1)
    return value.lstrip("@")

def _webapp_family_link() -> str:
    if settings.BOT_USERNAME:
        return f"https://t.me/{settings.BOT_USERNAME}?startapp=family"
    return ""

@router.post("/check-username")
def check_username(
    body: FamilyCheckUsernameIn,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    username = _normalize_username(body.username or "")
    if not username:
        raise HTTPException(400, "Missing username")
    rows = db.query(Guest, Profile).join(Profile, Profile.guest_id == Guest.id).filter(
        Guest.username.ilike(username)
    ).all()
    if not rows:
        return {"found": False}
    if len(rows) > 1:
        raise HTTPException(409, "Multiple users found")
    g, p = rows[0]
    name = p.full_name or f"{g.first_name or ''} {g.last_name or ''}".strip() or "—"
    return {"found": True, "guest_id": g.id, "name": name, "username": g.username}

@router.post("/invite-by-username")
async def invite_by_username(
    body: FamilyInviteByUsernameIn,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    username = _normalize_username(body.username or "")
    if not username:
        raise HTTPException(400, "Missing username")

    candidates = (
        db.query(Guest, Profile)
        .join(Profile, Profile.guest_id == Guest.id)
        .filter(Guest.username.ilike(username))
        .all()
    )
    if not candidates:
        raise HTTPException(404, "User not found")
    if len(candidates) > 1:
        raise HTTPException(409, "Multiple users found")
    other_guest, _profile = candidates[0]

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
        invitee_telegram_user_id=other_guest.telegram_user_id,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invite)
    db.commit()

    inviter_name = guest.profile.full_name if guest.profile else ""
    if not inviter_name:
        inviter_name = f"{guest.first_name or ''} {guest.last_name or ''}".strip() or "Гость"
    inviter_bd = guest.profile.birth_date.isoformat() if guest.profile and guest.profile.birth_date else "не указана"
    link = _webapp_family_link()
    try:
        await send_user_message(
            other_guest.telegram_user_id,
            (
                "<b>Приглашение в семью</b>\n"
                f"Пригласил(а): {inviter_name}\n"
                f"Дата рождения: {inviter_bd}\n\n"
                "Откройте мини‑приложение и перейдите в раздел «Семья».\n"
                + (f"Ссылка: {link}" if link else "Откройте через меню бота → Открыть приложение → Семья.")
            )
        )
    except Exception:
        pass
    return {"ok": True, "token": token}

@router.get("/invites/incoming", response_model=FamilyIncomingInviteOut | None)
def incoming_invite(
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    invite = db.query(InviteToken).filter(
        InviteToken.invitee_telegram_user_id == guest.telegram_user_id,
        InviteToken.status == "pending"
    ).order_by(InviteToken.created_at.desc()).first()
    if not invite:
        return None
    inviter = db.query(Guest).filter(Guest.id == invite.inviter_guest_id).one_or_none()
    inviter_name = "Гость"
    inviter_bd = None
    if inviter:
        profile = db.query(Profile).filter(Profile.guest_id == inviter.id).one_or_none()
        if profile and profile.full_name:
            inviter_name = profile.full_name
        if profile and profile.birth_date:
            inviter_bd = profile.birth_date
    return FamilyIncomingInviteOut(token=invite.token, inviter_name=inviter_name, inviter_birth_date=inviter_bd)

@router.post("/invite/{token}/accept")
async def accept_invite(
    token: str,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    invite = db.query(InviteToken).filter(InviteToken.token == token).one_or_none()
    if not invite:
        raise HTTPException(404, "Invite not found")
    if invite.status != "pending":
        raise HTTPException(400, "Invite not pending")
    if invite.invitee_telegram_user_id and invite.invitee_telegram_user_id != guest.telegram_user_id:
        raise HTTPException(403, "Not your invite")
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        invite.status = "declined"
        invite.declined_at = datetime.utcnow()
        db.add(invite)
        db.commit()
        raise HTTPException(400, "Invite expired")
    if guest.family_group_id and guest.family_group_id != invite.family_group_id:
        raise HTTPException(409, "Already in another family")
    guest.family_group_id = invite.family_group_id
    invite.status = "accepted"
    invite.accepted_at = datetime.utcnow()
    invite.used_by_guest_id = guest.id
    db.add(guest)
    db.add(invite)
    db.commit()

    inviter = db.query(Guest).filter(Guest.id == invite.inviter_guest_id).one_or_none()
    invitee_name = guest.profile.full_name if guest.profile else ""
    if not invitee_name:
        invitee_name = f"{guest.first_name or ''} {guest.last_name or ''}".strip() or "Гость"
    if inviter:
        try:
            await send_user_message(
                inviter.telegram_user_id,
                f"✅ Приглашение принято: {invitee_name}"
            )
        except Exception:
            pass
    return {"ok": True, "family_group_id": guest.family_group_id}

@router.post("/invite/{token}/decline")
async def decline_invite(
    token: str,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    invite = db.query(InviteToken).filter(InviteToken.token == token).one_or_none()
    if not invite:
        raise HTTPException(404, "Invite not found")
    if invite.status != "pending":
        raise HTTPException(400, "Invite not pending")
    if invite.invitee_telegram_user_id and invite.invitee_telegram_user_id != guest.telegram_user_id:
        raise HTTPException(403, "Not your invite")
    invite.status = "declined"
    invite.declined_at = datetime.utcnow()
    db.add(invite)
    db.commit()

    inviter = db.query(Guest).filter(Guest.id == invite.inviter_guest_id).one_or_none()
    invitee_name = guest.profile.full_name if guest.profile else ""
    if not invitee_name:
        invitee_name = f"{guest.first_name or ''} {guest.last_name or ''}".strip() or "Гость"
    if inviter:
        try:
            await send_user_message(
                inviter.telegram_user_id,
                f"❌ Приглашение отклонено: {invitee_name}"
            )
        except Exception:
            pass
    return {"ok": True}

@router.post("/invite/{token}/cancel")
def cancel_invite(
    token: str,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    invite = db.query(InviteToken).filter(InviteToken.token == token).one_or_none()
    if not invite:
        raise HTTPException(404, "Invite not found")
    if invite.status != "pending":
        raise HTTPException(400, "Invite not pending")
    if invite.inviter_guest_id != guest.id and invite.invitee_telegram_user_id != guest.telegram_user_id:
        raise HTTPException(403, "Forbidden")
    invite.status = "canceled"
    invite.declined_at = datetime.utcnow()
    db.add(invite)
    db.commit()
    return {"ok": True}

@router.post("/invite-by-username/cancel")
async def cancel_invite_by_username(
    body: FamilyInviteByUsernameIn,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    username = _normalize_username(body.username or "")
    if not username:
        raise HTTPException(400, "Missing username")
    invite = (
        db.query(InviteToken, Guest)
        .join(Guest, Guest.telegram_user_id == InviteToken.invitee_telegram_user_id)
        .filter(
            InviteToken.inviter_guest_id == guest.id,
            InviteToken.status == "pending",
            Guest.username.ilike(username),
        )
        .order_by(InviteToken.created_at.desc())
        .first()
    )
    if not invite:
        raise HTTPException(404, "Invite not found")
    token_row, invitee = invite
    token_row.status = "canceled"
    token_row.declined_at = datetime.utcnow()
    db.add(token_row)
    db.commit()
    try:
        await send_user_message(
            invitee.telegram_user_id,
            "Приглашение в семью отменено отправителем."
        )
    except Exception:
        pass
    return {"ok": True}

@router.post("/remove-partner")
async def remove_partner(
    body: FamilyRemovePartnerIn,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    if not guest.family_group_id:
        return {"ok": True}
    members = db.query(Guest).filter(Guest.family_group_id == guest.family_group_id).all()
    if len(members) <= 1:
        guest.family_group_id = None
        db.add(guest)
        db.commit()
        return {"ok": True}
    partner = None
    if body.partner_telegram_user_id:
        for m in members:
            if m.telegram_user_id == body.partner_telegram_user_id:
                partner = m
                break
    else:
        partner = next((m for m in members if m.telegram_user_id != guest.telegram_user_id), None)
    if not partner:
        return {"ok": True}
    if partner.telegram_user_id == guest.telegram_user_id:
        raise HTTPException(400, "Self remove not allowed")

    group_id = guest.family_group_id
    guest.family_group_id = None
    partner.family_group_id = None
    db.add(guest)
    db.add(partner)
    # cancel pending invites for this group
    db.query(InviteToken).filter(
        InviteToken.family_group_id == group_id,
        InviteToken.status == "pending"
    ).delete()
    # remove group if empty or one member
    db.query(FamilyGroup).filter(FamilyGroup.id == group_id).delete()
    db.commit()

    try:
        await send_user_message(
            partner.telegram_user_id,
            "Партнёр разъединил семью. Теперь вы не связаны."
        )
    except Exception:
        pass
    return {"ok": True}

@router.post("/leave")
async def leave_family(
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    if not guest.family_group_id:
        return {"ok": True, "family_group_id": None}
    group_id = guest.family_group_id
    # remove requester
    guest.family_group_id = None
    db.add(guest)
    db.commit()
    # cancel pending invites for this group
    db.query(InviteToken).filter(
        InviteToken.family_group_id == group_id,
        InviteToken.status == "pending"
    ).delete()
    # check remaining members
    remaining = db.query(Guest).filter(Guest.family_group_id == group_id).all()
    if len(remaining) <= 1:
        for g in remaining:
            g.family_group_id = None
            db.add(g)
        db.query(FamilyGroup).filter(FamilyGroup.id == group_id).delete()
    db.commit()
    # notify remaining member if exists
    if len(remaining) == 1:
        other = remaining[0]
        try:
            await send_user_message(
                other.telegram_user_id,
                "Партнёр разъединил семью. Теперь вы не связаны."
            )
        except Exception:
            pass
    return {"ok": True, "family_group_id": None}

# legacy alias
@router.post("/invite-by-name")
def invite_by_name_legacy(
    body: dict,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    username = body.get("username") or body.get("full_name") or ""
    return invite_by_username(FamilyInviteByUsernameIn(username=username), x_tg_initdata, x_invite_token, db)

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
