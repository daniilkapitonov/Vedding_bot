from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict

router = APIRouter(prefix="", tags=["temp-profile"])

_STORE: Dict[int, Dict[str, Any]] = {}
_FAMILY: Dict[int, Dict[str, Any]] = {}
_INVITES: Dict[int, Dict[str, Any]] = {}


class TempProfileIn(BaseModel):
    telegram_id: int
    data: Dict[str, Any]


@router.post("/profile/save")
def save_profile(body: TempProfileIn):
    _STORE[body.telegram_id] = body.data
    return {"ok": True}


@router.get("/profile/{telegram_id}")
def get_profile(telegram_id: int):
    return {"ok": True, "data": _STORE.get(telegram_id)}


class FamilyInviteIn(BaseModel):
    telegram_id: int
    full_name: str


class FamilySaveIn(BaseModel):
    telegram_id: int
    data: Dict[str, Any]


@router.post("/family/invite")
def invite_family(body: FamilyInviteIn):
    def normalize(value: str) -> str:
        return " ".join(value.strip().lower().split())

    needle = normalize(body.full_name)
    target_id = None
    for tid, data in _STORE.items():
        name = data.get("fullName") or data.get("full_name") or ""
        if normalize(name) == needle:
            target_id = tid
            break

    if target_id is None:
        return {"ok": False, "error": "not_found"}

    _INVITES[body.telegram_id] = {
        "full_name": body.full_name,
        "status": "sent",
        "confirmed": False,
        "target_id": target_id,
    }
    return {"ok": True, "invite": _INVITES[body.telegram_id]}


@router.post("/family/save")
def save_family(body: FamilySaveIn):
    _FAMILY[body.telegram_id] = body.data
    return {"ok": True}


@router.get("/family/{telegram_id}")
def get_family(telegram_id: int):
    return {
        "ok": True,
        "data": _FAMILY.get(telegram_id),
        "invite": _INVITES.get(telegram_id),
    }
