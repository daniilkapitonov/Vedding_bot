from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..schemas import TelegramAuthIn, MeOut
from ..db import get_db
from ..models import Guest, Profile
from ..config import settings
from ..services.telegram_auth import verify_telegram_init_data

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/telegram", response_model=MeOut)
def auth_telegram(body: TelegramAuthIn, db: Session = Depends(get_db)):
    try:
        user = verify_telegram_init_data(body.initData, settings.BOT_TOKEN)
    except ValueError as e:
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

    return MeOut(
        telegram_user_id=guest.telegram_user_id,
        first_name=guest.first_name,
        last_name=guest.last_name,
        username=guest.username
    )
