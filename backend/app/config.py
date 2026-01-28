from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    BOT_USERNAME: str | None = None
    ADMIN_IDS: str = ""
    WEDDING_DATE: str = "2026-07-25T16:00:00+03:00"
    WEBAPP_URL: str = "https://example.com"

    DATABASE_URL: str = "sqlite:///./data/app.db"

    # Public base url (for WebApp calling API directly outside docker)
    PUBLIC_API_BASE_URL: str = "http://localhost:8000"

    INTERNAL_SECRET: str = "change_me"
    ALLOW_DEV_AUTH: bool = False
    DEV_USER_ID: int = 1
    GOOGLE_SA_JSON_PATH: str | None = None

    @property
    def admin_id_set(self) -> set[int]:
        ids = [x.strip() for x in self.ADMIN_IDS.split(",") if x.strip()]
        return {int(x) for x in ids}

settings = Settings()
