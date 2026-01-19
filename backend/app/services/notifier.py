import httpx
from ..config import settings

async def notify_admins(event: str, payload: dict):
    """
    Simple approach: backend calls bot HTTP endpoint.
    Bot will send messages to admins.
    """
    url = "http://bot:8081/internal/notify"
    headers = {"x-internal-secret": settings.INTERNAL_SECRET}
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            await client.post(url, json={"event": event, "payload": payload}, headers=headers)
        except Exception:
            # non-fatal
            pass

async def send_admin_message(text: str):
    """
    Send direct Telegram messages to admins via Bot API.
    """
    if not settings.BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    admin_ids = settings.admin_id_set
    async with httpx.AsyncClient(timeout=8) as client:
        for admin_id in admin_ids:
            try:
                await client.post(url, json={
                    "chat_id": admin_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                })
            except Exception:
                pass
