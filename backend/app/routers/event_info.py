from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import EventInfo
from ..schemas import EventInfoOut

router = APIRouter(prefix="/api/event", tags=["event"])

@router.get("", response_model=EventInfoOut)
def get_event_info(db: Session = Depends(get_db)):
    row = db.query(EventInfo).first()
    if not row:
        row = EventInfo(content="Заглушка: здесь будет общая информация о мероприятии.")
        db.add(row)
        db.commit()
        db.refresh(row)
    return EventInfoOut(content=row.content, updated_at=row.updated_at.isoformat())
