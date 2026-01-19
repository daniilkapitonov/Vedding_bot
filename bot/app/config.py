import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com")
API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "change_me")
