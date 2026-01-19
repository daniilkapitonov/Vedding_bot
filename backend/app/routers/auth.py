from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
import logging

from ..schemas import TelegramAuthIn, MeOut
from ..db import get_db
from ..models import Guest, Profile
from ..config import settings
from ..services.telegram_auth import verify_telegram_init_data, get_guest_from_invite

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)

@router.post("/telegram", response_model=MeOut)
def auth_telegram(
    body: TelegramAuthIn,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    init_data = body.initData or x_tg_initdata or ""
    try:
        if init_data:
            user = verify_telegram_init_data(init_data, settings.BOT_TOKEN)
        elif x_invite_token:
            guest = get_guest_from_invite(x_invite_token, db)
            return MeOut(
                telegram_user_id=guest.telegram_user_id,
                first_name=guest.first_name,
                last_name=guest.last_name,
                username=guest.username
            )
        else:
            raise ValueError("Missing initData")
    except ValueError as e:
        if x_invite_token:
            try:
                guest = get_guest_from_invite(x_invite_token, db)
                return MeOut(
                    telegram_user_id=guest.telegram_user_id,
                    first_name=guest.first_name,
                    last_name=guest.last_name,
                    username=guest.username
                )
            except ValueError as e2:
                logger.warning("auth_telegram failed: %s (len=%s)", str(e2), len(init_data))
                raise HTTPException(status_code=401, detail=str(e2))
        logger.warning("auth_telegram failed: %s (len=%s)", str(e), len(init_data))
        raise HTTPException(status_code=401, detail=str(e))

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

    return MeOut(
        telegram_user_id=guest.telegram_user_id,
        first_name=guest.first_name,
        last_name=guest.last_name,
        username=guest.username
    )
