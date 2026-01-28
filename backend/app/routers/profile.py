from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import date, datetime
import logging

from ..db import get_db
from ..models import Guest, Profile, ChangeLog
from ..schemas import ProfileIn, ProfileOut, ExtraIn, PartnerLinkIn, ProfileExistsOut
from ..config import settings
from ..services.telegram_auth import verify_telegram_init_data, get_guest_from_invite
from ..services.notifier import send_admin_message, send_user_message
from ..services.sheets_queue import enqueue_sheet_sync

router = APIRouter(prefix="/api", tags=["profile"])
legacy_router = APIRouter(tags=["profile-legacy"])
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
    out = [x for x in (s.strip() for s in v.split(",")) if x]
    return ["Не пью алкоголь" if x == "Не пью" else x for x in out]

def _join_csv(v: list[str]) -> str:
    normalized = []
    for item in v:
        value = item.strip()
        if not value:
            continue
        if value == "Не пью":
            value = "Не пью алкоголь"
        normalized.append(value)
    return ",".join(normalized)

def _fmt_value(value) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, list):
        return ", ".join([str(v) for v in value if v]) or "—"
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    if isinstance(value, date):
        return value.isoformat()
    return str(value)

def _diff(before: dict, after: dict, labels: dict) -> list[tuple[str, str, str]]:
    changes = []
    for key, label in labels.items():
        if before.get(key) != after.get(key):
            changes.append((label, _fmt_value(before.get(key)), _fmt_value(after.get(key))))
    return changes

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
        is_best_friend=p.is_best_friend,
        has_plus_one_requested=p.has_plus_one_requested,
        plus_one_partner_username=p.plus_one_partner_username,
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
        welcome_seen_at=p.welcome_seen_at.isoformat() if p.welcome_seen_at else None,
    )

@router.get("/profile/exists", response_model=ProfileExistsOut)
def profile_exists(
    x_tg_initdata: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not x_tg_initdata:
        return ProfileExistsOut(exists=False)
    try:
        user = verify_telegram_init_data(x_tg_initdata, settings.BOT_TOKEN)
    except ValueError:
        return ProfileExistsOut(exists=False)
    tg_id = int(user["id"])
    guest = db.query(Guest).filter(Guest.telegram_user_id == tg_id).one_or_none()
    if not guest or not guest.profile:
        return ProfileExistsOut(exists=False)
    p = guest.profile
    return ProfileExistsOut(exists=True, welcome_seen_at=p.welcome_seen_at.isoformat() if p.welcome_seen_at else None)

@router.post("/profile", response_model=ProfileOut)
async def upsert_profile(
    body: ProfileIn,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    p: Profile = guest.profile

    before = {
        "rsvp_status": p.rsvp_status,
        "full_name": p.full_name,
        "birth_date": p.birth_date,
        "gender": p.gender,
        "side": p.side,
        "is_relative": p.is_relative,
        "food_pref": p.food_pref,
        "food_allergies": p.food_allergies,
        "alcohol_prefs": _split_csv(p.alcohol_prefs_csv),
        "phone": guest.phone,
        "has_plus_one_requested": p.has_plus_one_requested,
    }

    # RSVP=No => only store minimal and lock in UI logic
    p.rsvp_status = body.rsvp_status
    if body.has_plus_one_requested is not None:
        p.has_plus_one_requested = bool(body.has_plus_one_requested)

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
        setattr(p, field, value)

    # phone on Guest
    guest.phone = body.phone

    # alcohol
    p.alcohol_prefs_csv = _join_csv(body.alcohol_prefs)

    db.add(guest)
    db.add(p)
    after = {
        "rsvp_status": p.rsvp_status,
        "full_name": p.full_name,
        "birth_date": p.birth_date,
        "gender": p.gender,
        "side": p.side,
        "is_relative": p.is_relative,
        "food_pref": p.food_pref,
        "food_allergies": p.food_allergies,
        "alcohol_prefs": _split_csv(p.alcohol_prefs_csv),
        "phone": guest.phone,
        "has_plus_one_requested": p.has_plus_one_requested,
    }
    labels = {
        "rsvp_status": "RSVP",
        "full_name": "ФИО",
        "birth_date": "Дата рождения",
        "gender": "Пол",
        "side": "Сторона",
        "is_relative": "Родственник",
        "food_pref": "Еда",
        "food_allergies": "Аллергии",
        "alcohol_prefs": "Алкоголь",
        "phone": "Телефон",
        "has_plus_one_requested": "+1",
    }
    changes = _diff(before, after, labels)
    for label, old, new in changes:
        db.add(ChangeLog(guest_id=guest.id, field=label, old_value=old, new_value=new))
    db.commit()

    # enqueue sheet sync (non-blocking)
    try:
        enqueue_sheet_sync(db, guest.telegram_user_id, reason="profile_save")
    except Exception:
        pass

    # Send +1 invite reminder once per save when enabled
    if before.get("has_plus_one_requested") is False and p.has_plus_one_requested:
        try:
            name = p.full_name or f"{guest.first_name or ''} {guest.last_name or ''}".strip() or "Гость"
            msg = (
                f"{name} приглашает вас пойти с ним/ней на свадьбу Капитоновых 💍\n"
                f"Дата: 25.07.2026\n"
                f"Откройте приглашение и заполните анкету: https://t.me/kapa_vedding_bot/welcome_to_wedding"
            )
            await send_user_message(guest.telegram_user_id, msg)
            p.plus_one_invite_sent_at = datetime.utcnow()
            db.add(p)
            db.commit()
        except Exception:
            pass

    if changes:
        try:
            name = p.full_name or f"{guest.first_name or ''} {guest.last_name or ''}".strip() or "Гость"
            lines = [f"<b>Анкета обновлена</b>", f"{name} (id {guest.id})", ""]
            for label, old, new in changes:
                lines.append(f"{label}: {old} → {new}")
            await send_admin_message("\n".join(lines), category="system", db=db)
        except Exception:
            pass

    return get_profile(x_tg_initdata, x_invite_token, db)

@router.post("/profile/welcome-seen")
def mark_welcome_seen(
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    p: Profile = guest.profile
    p.welcome_seen_at = datetime.utcnow()
    db.add(p)
    db.commit()
    return {"ok": True, "welcome_seen_at": p.welcome_seen_at.isoformat()}
@router.post("/extra", response_model=ProfileOut)
async def save_extra(
    body: ExtraIn,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    guest = _guest_from_initdata(x_tg_initdata, x_invite_token, db)
    p: Profile = guest.profile

    before = {
        "extra_known_since": p.extra_known_since,
        "extra_memory": p.extra_memory,
        "extra_fact": p.extra_fact,
        "photos": _split_csv(p.photos_csv),
    }

    for field, value in [
        ("extra_known_since", body.extra_known_since),
        ("extra_memory", body.extra_memory),
        ("extra_fact", body.extra_fact),
    ]:
        setattr(p, field, value)

    # photos max 5
    photos = body.photos[:5]
    p.photos_csv = _join_csv(photos)

    db.add(p)
    after = {
        "extra_known_since": p.extra_known_since,
        "extra_memory": p.extra_memory,
        "extra_fact": p.extra_fact,
        "photos": _split_csv(p.photos_csv),
    }
    labels = {
        "extra_known_since": "Кого знаете ближе",
        "extra_memory": "Воспоминание",
        "extra_fact": "Факт",
        "photos": "Фото",
    }
    changes = _diff(before, after, labels)
    for label, old, new in changes:
        db.add(ChangeLog(guest_id=guest.id, field=label, old_value=old, new_value=new))
    db.commit()
    if changes:
        try:
            name = p.full_name or f"{guest.first_name or ''} {guest.last_name or ''}".strip() or "Гость"
            lines = [f"<b>Доп. информация обновлена</b>", f"{name} (id {guest.id})", ""]
            for label, old, new in changes:
                lines.append(f"{label}: {old} → {new}")
            await send_admin_message("\n".join(lines), category="system", db=db)
        except Exception:
            pass
    return get_profile(x_tg_initdata, x_invite_token, db)

# Legacy routes (no /api prefix) for cached clients
legacy_router.add_api_route("/profile", get_profile, methods=["GET"], response_model=ProfileOut)
legacy_router.add_api_route("/profile", upsert_profile, methods=["POST"], response_model=ProfileOut)
legacy_router.add_api_route("/profile/exists", profile_exists, methods=["GET"], response_model=ProfileExistsOut)
legacy_router.add_api_route("/profile/welcome-seen", mark_welcome_seen, methods=["POST"])
legacy_router.add_api_route("/extra", save_extra, methods=["POST"], response_model=ProfileOut)

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

    before = {
        "partner_guest_id": p.partner_guest_id,
        "partner_pending_full_name": p.partner_pending_full_name,
        "partner_pending_birth_date": p.partner_pending_birth_date,
    }

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

    db.add(p)
    after = {
        "partner_guest_id": p.partner_guest_id,
        "partner_pending_full_name": p.partner_pending_full_name,
        "partner_pending_birth_date": p.partner_pending_birth_date,
    }
    labels = {
        "partner_guest_id": "Партнёр (ID)",
        "partner_pending_full_name": "Партнёр (ожид.)",
        "partner_pending_birth_date": "ДР партнёра (ожид.)",
    }
    changes = _diff(before, after, labels)
    for label, old, new in changes:
        db.add(ChangeLog(guest_id=guest.id, field=label, old_value=old, new_value=new))
    db.commit()
    if changes:
        try:
            name = p.full_name or f"{guest.first_name or ''} {guest.last_name or ''}".strip() or "Гость"
            lines = [f"<b>Партнёр обновлён</b>", f"{name} (id {guest.id})", ""]
            for label, old, new in changes:
                lines.append(f"{label}: {old} → {new}")
            await send_admin_message("\n".join(lines), category="system", db=db)
        except Exception:
            pass
    return get_profile(x_tg_initdata, x_invite_token, db)
