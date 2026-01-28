import json
import logging
from sqlalchemy.orm import Session

from ..models import SheetSyncJob

logger = logging.getLogger(__name__)

def enqueue_sheet_sync(db: Session, telegram_id: int | None, reason: str = "update") -> None:
    job = SheetSyncJob(
        type="sync_guest" if telegram_id else "sync_all",
        telegram_id=telegram_id,
        status="pending",
        attempts=0,
        payload=json.dumps({"reason": reason}),
    )
    db.add(job)
    db.commit()

def enqueue_sync_all(db: Session, reason: str = "admin") -> None:
    enqueue_sheet_sync(db, None, reason=reason)
