from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List

class TelegramAuthIn(BaseModel):
    initData: str

class MeOut(BaseModel):
    telegram_user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None

class ProfileIn(BaseModel):
    rsvp_status: str = Field(pattern="^(yes|no|maybe)$")

    full_name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(default=None, pattern="^(male|female|other)?$")
    phone: Optional[str] = None
    side: Optional[str] = Field(default=None, pattern="^(groom|bride|both)?$")
    is_relative: bool = False

    food_pref: Optional[str] = Field(default=None, pattern="^(fish|meat|vegan)?$")
    food_allergies: Optional[str] = None

    alcohol_prefs: List[str] = []

class ProfileOut(BaseModel):
    rsvp_status: str
    full_name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    side: Optional[str] = None
    is_relative: bool

    food_pref: Optional[str] = None
    food_allergies: Optional[str] = None
    alcohol_prefs: List[str] = []

    partner_guest_id: Optional[int] = None
    partner_pending_full_name: Optional[str] = None
    partner_pending_birth_date: Optional[date] = None
    photos: List[str] = []

    extra_known_since: Optional[str] = None
    extra_memory: Optional[str] = None
    extra_fact: Optional[str] = None

class ExtraIn(BaseModel):
    extra_known_since: Optional[str] = Field(default=None, pattern="^(groom|bride|both)?$")
    extra_memory: Optional[str] = None
    extra_fact: Optional[str] = None
    photos: List[str] = []  # telegram file_id

class PartnerLinkIn(BaseModel):
    full_name: str
    birth_date: date

class EventInfoOut(BaseModel):
    content: str
    updated_at: str

class AdminEventInfoIn(BaseModel):
    content: str

class BroadcastIn(BaseModel):
    text: str
    group_ids: List[int] = []   # empty => all
