import httpx
import logging
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal
from ..models import AdminSettings

logger = logging.getLogger(__name__)

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
        except Exception as e:
            logger.warning("notify_admins failed: %s", str(e))
            # non-fatal
            pass

def _system_notifications_enabled(db: Session, admin_id: int) -> bool:
    row = db.query(AdminSettings).filter(AdminSettings.admin_id == admin_id).one_or_none()
    if not row:
        return True
    return bool(row.system_notifications_enabled)

async def send_admin_message(text: str, category: str = "system", db: Session | None = None) -> bool:
    """
    Send direct Telegram messages to admins via Bot API.
    """
    if not settings.BOT_TOKEN:
        logger.warning("send_admin_message: missing BOT_TOKEN")
        return False
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    admin_ids = settings.admin_id_set
    if not admin_ids:
        return False
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    sent_any = False
    async with httpx.AsyncClient(timeout=8) as client:
        for admin_id in admin_ids:
            if category != "question" and not _system_notifications_enabled(db, admin_id):
                continue
            try:
                resp = await client.post(url, json={
                    "chat_id": admin_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                })
                if resp.status_code >= 200 and resp.status_code < 300:
                    sent_any = True
                else:
                    logger.warning("send_admin_message status=%s body=%s", resp.status_code, resp.text[:200])
            except Exception as e:
                logger.warning("send_admin_message failed: %s", str(e))
                continue
    if close_db:
        db.close()
    return sent_any
