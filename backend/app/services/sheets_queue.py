import json
import logging
from sqlalchemy.orm import Session

from ..models import SheetSyncJob

logger = logging.getLogger(__name__)

def _enqueue(db: Session, job_type: str, telegram_id: int | None, reason: str) -> None:
    job = SheetSyncJob(
        type=job_type,
        telegram_id=telegram_id,
        status="pending",
        attempts=0,
        payload=json.dumps({"reason": reason}),
    )
    db.add(job)
    db.commit()

def enqueue_sheet_sync(db: Session, telegram_id: int | None, reason: str = "update") -> None:
    _enqueue(db, "sync_guest" if telegram_id else "sync_all", telegram_id, reason)

def enqueue_sync_all(db: Session, reason: str = "admin") -> None:
    enqueue_sheet_sync(db, None, reason=reason)

def enqueue_delete_guest(db: Session, telegram_id: int, reason: str = "delete") -> None:
    _enqueue(db, "delete_guest", telegram_id, reason)

def enqueue_clear_all(db: Session, reason: str = "clear") -> None:
    _enqueue(db, "clear_all", None, reason)
