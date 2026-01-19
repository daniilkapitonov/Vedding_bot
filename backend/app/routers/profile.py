from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import date
import logging

from ..db import get_db
from ..models import Guest, Profile, ChangeLog
from ..schemas import ProfileIn, ProfileOut, ExtraIn, PartnerLinkIn
from ..config import settings
from ..services.telegram_auth import verify_telegram_init_data, get_guest_from_invite
from ..services.notifier import notify_admins

router = APIRouter(prefix="/api", tags=["profile"])
logger = logging.getLogger(__name__)

def _guest_from_initdata(initdata: str | None, invite_token: str | None, db: Session) -> Guest:
    try:
        if initdata:
            user = verify_telegram_init_data(initdata, settings.BOT_TOKEN)
        elif invite_token:
            return get_guest_from_invite(invite_token, db)
        else:
            raise ValueError("Missing initData")
    except ValueError as e:
        if invite_token:
            try:
                return get_guest_from_invite(invite_token, db)
            except ValueError as e2:
                logger.warning("profile auth failed: %s (len=%s)", str(e2), len(initdata or ""))
                raise HTTPException(401, str(e2))
        logger.warning("profile auth failed: %s (len=%s)", str(e), len(initdata or ""))
        raise HTTPException(401, str(e))
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
    elif not guest.profile:
        db.add(Profile(guest_id=guest.id))
        db.commit()
        db.refresh(guest)
    return guest

def _split_csv(v: str | None) -> list[str]:
    if not v:
        return []
    return [x for x in (s.strip() for s in v.split(",")) if x]

def _join_csv(v: list[str]) -> str:
    return ",".join([x.strip() for x in v if x.strip()])

async def _log_change(db: Session, guest_id: int, field: str, old, new):
    if str(old) == str(new):
        return
    db.add(ChangeLog(guest_id=guest_id, field=field, old_value=str(old) if old is not None else None, new_value=str(new) if new is not None else None))
    db.commit()
    await notify_admins("profile_changed", {"guest_id": guest_id, "field": field, "old": old, "new": new})

@router.get("/profile", response_model=ProfileOut)
def get_profile(
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    p = guest.profile
    return ProfileOut(
        rsvp_status=p.rsvp_status,
        full_name=p.full_name,
        birth_date=p.birth_date,
        gender=p.gender,
        phone=guest.phone,
        side=p.side,
        is_relative=p.is_relative,
        food_pref=p.food_pref,
        food_allergies=p.food_allergies,
        alcohol_prefs=_split_csv(p.alcohol_prefs_csv),
        partner_guest_id=p.partner_guest_id,
        partner_pending_full_name=p.partner_pending_full_name,
        partner_pending_birth_date=p.partner_pending_birth_date,
        photos=_split_csv(p.photos_csv),
        extra_known_since=p.extra_known_since,
        extra_memory=p.extra_memory,
        extra_fact=p.extra_fact,
    )

@router.post("/profile", response_model=ProfileOut)
async def upsert_profile(
    body: ProfileIn,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    p: Profile = guest.profile

    # RSVP=No => only store minimal and lock in UI logic
    old_rsvp = p.rsvp_status
    p.rsvp_status = body.rsvp_status
    await _log_change(db, guest.id, "rsvp_status", old_rsvp, p.rsvp_status)

    # Basic fields
    for field, value in [
        ("full_name", body.full_name),
        ("birth_date", body.birth_date),
        ("gender", body.gender),
        ("side", body.side),
        ("is_relative", body.is_relative),
        ("food_pref", body.food_pref),
        ("food_allergies", body.food_allergies),
    ]:
        old = getattr(p, field)
        setattr(p, field, value)
        await _log_change(db, guest.id, field, old, value)

    # phone on Guest
    old_phone = guest.phone
    guest.phone = body.phone
    await _log_change(db, guest.id, "phone", old_phone, guest.phone)

    # alcohol
    old_alc = p.alcohol_prefs_csv
    p.alcohol_prefs_csv = _join_csv(body.alcohol_prefs)
    await _log_change(db, guest.id, "alcohol_prefs", old_alc, p.alcohol_prefs_csv)

    db.add(guest)
    db.add(p)
    db.commit()

    return get_profile(x_tg_initdata, db)

@router.post("/extra", response_model=ProfileOut)
async def save_extra(
    body: ExtraIn,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    p: Profile = guest.profile

    for field, value in [
        ("extra_known_since", body.extra_known_since),
        ("extra_memory", body.extra_memory),
        ("extra_fact", body.extra_fact),
    ]:
        old = getattr(p, field)
        setattr(p, field, value)
        await _log_change(db, guest.id, field, old, value)

    # photos max 5
    photos = body.photos[:5]
    old_ph = p.photos_csv
    p.photos_csv = _join_csv(photos)
    await _log_change(db, guest.id, "photos", old_ph, p.photos_csv)

    db.add(p)
    db.commit()
    return get_profile(x_tg_initdata, db)

@router.post("/partner/link", response_model=ProfileOut)
async def link_partner(
    body: PartnerLinkIn,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    p: Profile = guest.profile

    # search by exact full_name + birth_date
    candidate = (
        db.query(Profile)
        .filter(Profile.full_name == body.full_name)
        .filter(Profile.birth_date == body.birth_date)
        .one_or_none()
    )

    old_partner = p.partner_guest_id
    old_pending_name = p.partner_pending_full_name
    old_pending_bd = p.partner_pending_birth_date

    if candidate and candidate.guest_id != p.guest_id:
        p.partner_guest_id = candidate.guest_id
        p.partner_pending_full_name = None
        p.partner_pending_birth_date = None

        # also link back (optional, symmetrical)
        other = candidate
        if other.partner_guest_id is None:
            other.partner_guest_id = p.guest_id
            db.add(other)
    else:
        p.partner_guest_id = None
        p.partner_pending_full_name = body.full_name
        p.partner_pending_birth_date = body.birth_date

    await _log_change(db, guest.id, "partner_guest_id", old_partner, p.partner_guest_id)
    await _log_change(db, guest.id, "partner_pending_full_name", old_pending_name, p.partner_pending_full_name)
    await _log_change(db, guest.id, "partner_pending_birth_date", old_pending_bd, p.partner_pending_birth_date)

    db.add(p)
    db.commit()
    return get_profile(x_tg_initdata, db)
