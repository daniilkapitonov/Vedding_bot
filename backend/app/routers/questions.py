from fastapi import APIRouter, Header, HTTPException, Depends
import logging

from sqlalchemy.orm import Session

from ..config import settings
from ..services.telegram_auth import verify_telegram_init_data, get_guest_from_invite
from ..services.notifier import send_admin_message
from ..db import get_db

router = APIRouter(prefix="/api/questions", tags=["questions"])
logger = logging.getLogger(__name__)


def _build_sender_link(user: dict) -> str:
    username = user.get("username")
    user_id = user.get("id")
    if username:
        return f"https://t.me/{username}"
    if user_id and user_id > 0:
        return f"tg://user?id={user_id}"
    return ""


@router.post("")
async def send_question(
    body: dict,
    x_tg_initdata: str | None = Header(default=None),
    x_invite_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user: dict | None = None
    if x_tg_initdata:
        try:
            user = verify_telegram_init_data(x_tg_initdata, settings.BOT_TOKEN)
        except ValueError as e:
            logger.warning("questions: invalid initData (%s)", str(e))
            raise HTTPException(401, str(e))
    elif x_invite_token:
        try:
            guest = get_guest_from_invite(x_invite_token, db)
            name = guest.first_name or ""
            if guest.last_name:
                name = f"{name} {guest.last_name}".strip()
            user = {"id": guest.telegram_user_id, "first_name": name or "Гость"}
        except Exception:
            logger.warning("questions: invalid invite token")
            raise HTTPException(401, "Invalid invite token")
    if not user:
        logger.warning("questions: missing initData")
        raise HTTPException(401, "Missing initData")
    text = (body.get("text") or "").strip()
    if not text:
        logger.warning("questions: empty text")
        raise HTTPException(400, "Empty question")

    first = user.get("first_name") or ""
    last = user.get("last_name") or ""
    name = (f"{first} {last}").strip() or "Гость"
    username = user.get("username")
    user_id = user.get("id")
    link = _build_sender_link(user)
    link_part = f"\nСсылка: {link}" if link else ""
    uname_part = f"@{username}" if username else ""
    sender = f"{name} {uname_part}".strip()

    message = (
        f"<b>Вопрос от гостя</b>\n"
        f"{text}\n\n"
        f"Отправитель: {sender}\n"
        f"ID: {user_id}{link_part}"
    )

    if not settings.BOT_TOKEN:
        logger.error("questions: missing BOT_TOKEN in backend env")
        raise HTTPException(500, "Missing BOT_TOKEN")

    await send_admin_message(message)

    return {"ok": True}
