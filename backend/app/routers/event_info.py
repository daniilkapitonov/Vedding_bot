from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
import json
from datetime import datetime
from ..db import get_db
from ..models import EventInfo, EventContent, EventTiming, Guest, Profile
from ..schemas import EventInfoOut, EventTimingOut
from ..config import settings
from ..services.telegram_auth import verify_telegram_init_data

router = APIRouter(prefix="/api/event-info", tags=["event"])
legacy_router = APIRouter(prefix="/api/event", tags=["event"])

DEFAULT_EVENT_CONTENT = {
    "event_location_text": "Ресторан La Provincia, Калужская площадь, 1, стр. 4",
    "dresscode_text": "Тёплые нейтральные оттенки, пастельные акценты.",
    "contacts_text": "Организатор: +7 (906) 775-29-69, TG: @D_Kapa",
    "gifts_text": "Лучший подарок — вклад в наше путешествие или сертификат.",
    "faq_text": "Можно ли взять +1? — Да, укажите в разделе “Семья”.\nЕсть ли дресс-код? — Тёплые нейтральные оттенки.\nМожно ли фото? — Конечно, будем рады.",
    "how_to_add_partner_text": "Откройте раздел «Семья» и отправьте приглашение по Telegram нику (@username).",
}

DEFAULT_TIMING = [
    {"time": "16:00", "title": "Сбор гостей"},
    {"time": "17:00", "title": "Церемония"},
    {"time": "18:00", "title": "Банкет"},
    {"time": "21:30", "title": "Торт"},
]

@legacy_router.get("", response_model=EventInfoOut)
def get_event_info(db: Session = Depends(get_db)):
    row = db.query(EventInfo).first()
    if not row:
        row = EventInfo(content="Заглушка: здесь будет общая информация о мероприятии.")
        db.add(row)
        db.commit()
        db.refresh(row)
    return EventInfoOut(content=row.content, updated_at=row.updated_at.isoformat())

def _seed_event_content(db: Session) -> dict:
    out = {}
    for key, default_text in DEFAULT_EVENT_CONTENT.items():
        row = db.query(EventContent).filter(EventContent.key == key).one_or_none()
        if not row:
            row = EventContent(key=key, value_text=default_text)
            db.add(row)
            db.commit()
            db.refresh(row)
        out[key] = row.value_text
    return out

@router.get("/content")
def get_event_content(db: Session = Depends(get_db)):
    data = _seed_event_content(db)
    return data

def _get_timing(db: Session, group: int) -> list[dict]:
    row = db.query(EventTiming).filter(EventTiming.group == group).one_or_none()
    if not row:
        row = EventTiming(group=group, value_json=json.dumps(DEFAULT_TIMING, ensure_ascii=False))
        db.add(row)
        db.commit()
        db.refresh(row)
    try:
        return json.loads(row.value_json or "[]")
    except Exception:
        return DEFAULT_TIMING

@router.get("/timing/me", response_model=EventTimingOut)
def get_timing_for_user(
    x_tg_initdata: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not x_tg_initdata:
        items = _get_timing(db, 2)
        return EventTimingOut(items=items)
    user = verify_telegram_init_data(x_tg_initdata, settings.BOT_TOKEN)
    tg_id = int(user["id"])
    guest = db.query(Guest).filter(Guest.telegram_user_id == tg_id).one_or_none()
    if not guest or not guest.profile:
        items = _get_timing(db, 2)
        return EventTimingOut(items=items)
    p: Profile = guest.profile
    group = 1 if (p.is_relative or p.is_best_friend) else 2
    items = _get_timing(db, group)
    return EventTimingOut(items=items)
