from fastapi import APIRouter, Header, HTTPException
import httpx

from ..config import settings
from ..services.telegram_auth import verify_telegram_init_data

router = APIRouter(prefix="/api/questions", tags=["questions"])


def _build_sender_link(user: dict) -> str:
    username = user.get("username")
    user_id = user.get("id")
    if username:
        return f"https://t.me/{username}"
    if user_id:
        return f"tg://user?id={user_id}"
    return ""


@router.post("")
async def send_question(
    body: dict,
    x_tg_initdata: str | None = Header(default=None),
):
    if not x_tg_initdata:
        raise HTTPException(401, "Missing initData")
    user = verify_telegram_init_data(x_tg_initdata, settings.BOT_TOKEN)
    text = (body.get("text") or "").strip()
    if not text:
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

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=8) as client:
        for admin_id in settings.admin_id_set:
            try:
                await client.post(url, json={
                    "chat_id": admin_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                })
            except Exception:
                # ignore per-admin failures
                pass

    return {"ok": True}
