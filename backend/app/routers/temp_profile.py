from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="", tags=["temp-profile"])


@router.post("/profile/save")
def save_profile():
    raise HTTPException(status_code=410, detail="Temp profile disabled. Use /api/profile.")


@router.get("/profile/{telegram_id}")
def get_profile(telegram_id: int):
    raise HTTPException(status_code=410, detail="Temp profile disabled. Use /api/profile.")


@router.post("/family/invite")
def invite_family():
    raise HTTPException(status_code=410, detail="Temp family disabled. Use /api/family.")


@router.post("/family/save")
def save_family():
    raise HTTPException(status_code=410, detail="Temp family disabled. Use /api/family.")


@router.get("/family/{telegram_id}")
def get_family(telegram_id: int):
    raise HTTPException(status_code=410, detail="Temp family disabled. Use /api/family.")
