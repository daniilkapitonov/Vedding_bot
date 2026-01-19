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
