from sqlalchemy import String, Integer, Boolean, Date, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date

from .db import Base

class Guest(Base):
    __tablename__ = "guests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    family_group_id: Mapped[int | None] = mapped_column(ForeignKey("family_groups.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship(
        "Profile",
        back_populates="guest",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="Profile.guest_id",
    )

    family_group = relationship("FamilyGroup", back_populates="members", foreign_keys=[family_group_id])

class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (UniqueConstraint("guest_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guest_id: Mapped[int] = mapped_column(ForeignKey("guests.id"), index=True)

    rsvp_status: Mapped[str] = mapped_column(String(16), default="unknown")  # yes/no/maybe/unknown

    full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)  # male/female/other
    side: Mapped[str | None] = mapped_column(String(16), nullable=True)    # groom/bride/both
    is_relative: Mapped[bool] = mapped_column(Boolean, default=False)

    food_pref: Mapped[str | None] = mapped_column(String(16), nullable=True)  # fish/meat/vegan
    food_allergies: Mapped[str | None] = mapped_column(Text, nullable=True)

    alcohol_prefs_csv: Mapped[str | None] = mapped_column(Text, nullable=True) # multi: "wine,beer,..."

    extra_known_since: Mapped[str | None] = mapped_column(String(32), nullable=True)  # groom/bride/both -> drives questions
    extra_memory: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_fact: Mapped[str | None] = mapped_column(Text, nullable=True)

    photos_csv: Mapped[str | None] = mapped_column(Text, nullable=True)  # up to 5 Telegram file_id
    welcome_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Partner/children linking
    partner_guest_id: Mapped[int | None] = mapped_column(ForeignKey("guests.id"), nullable=True)
    partner_pending_full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    partner_pending_birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    guest = relationship("Guest", back_populates="profile", foreign_keys=[guest_id])

class EventInfo(Base):
    __tablename__ = "event_info"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text, default="Заглушка: здесь будет общая информация о мероприятии.")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FamilyGroup(Base):
    __tablename__ = "family_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    members = relationship("Guest", back_populates="family_group", cascade="all")

class InviteToken(Base):
    __tablename__ = "invite_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    family_group_id: Mapped[int] = mapped_column(ForeignKey("family_groups.id"), index=True)
    inviter_guest_id: Mapped[int] = mapped_column(ForeignKey("guests.id"), index=True)
    used_by_guest_id: Mapped[int | None] = mapped_column(ForeignKey("guests.id"), nullable=True)
    invitee_telegram_user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    declined_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class FamilyProfile(Base):
    __tablename__ = "family_profiles"
    __table_args__ = (UniqueConstraint("guest_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guest_id: Mapped[int] = mapped_column(ForeignKey("guests.id"), index=True)

    with_partner: Mapped[bool] = mapped_column(Boolean, default=False)
    partner_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    children_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Group(Base):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)

class GroupMember(Base):
    __tablename__ = "group_members"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    guest_id: Mapped[int] = mapped_column(ForeignKey("guests.id"), index=True)

class ChangeLog(Base):
    __tablename__ = "change_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guest_id: Mapped[int] = mapped_column(Integer, index=True)
    field: Mapped[str] = mapped_column(String(128))
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AdminSettings(Base):
    __tablename__ = "admin_settings"
    admin_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AppSettings(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
