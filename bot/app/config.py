import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com")
_api_base = os.getenv("API_BASE_URL", "http://backend:8000").strip()
_api_base = _api_base.rstrip("/")
if _api_base.endswith("/api"):
    _api_base = _api_base[:-4]
API_BASE_URL = _api_base
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "change_me")
