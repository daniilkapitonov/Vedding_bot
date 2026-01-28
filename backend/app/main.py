from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .db import Base, engine
from .routers import auth, profile, event_info, admin, family, questions

app = FastAPI(title="Wedding TG Backend")

# CORS: allow WebApp to call API locally
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP; позже сузим до конкретного домена WebApp
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(event_info.router)
if hasattr(event_info, "legacy_router"):
    app.include_router(event_info.legacy_router)
app.include_router(admin.router)
app.include_router(family.router)
app.include_router(questions.router)

def _legacy_notice():
    return {"ok": False, "detail": "Use /api/* endpoints"}

app.add_api_route("/api/ui-settings", admin.get_ui_settings_public, methods=["GET"])

def _ensure_family_group_column():
    if not engine.url.get_backend_name().startswith("sqlite"):
        return
    with engine.begin() as conn:
        cols = conn.execute(text("PRAGMA table_info(guests)")).fetchall()
        col_names = {row[1] for row in cols}
        if "family_group_id" not in col_names:
            conn.execute(text("ALTER TABLE guests ADD COLUMN family_group_id INTEGER"))

        cols = conn.execute(text("PRAGMA table_info(profiles)")).fetchall()
        col_names = {row[1] for row in cols}
        if "welcome_seen_at" not in col_names:
            conn.execute(text("ALTER TABLE profiles ADD COLUMN welcome_seen_at DATETIME"))
        if "is_best_friend" not in col_names:
            conn.execute(text("ALTER TABLE profiles ADD COLUMN is_best_friend BOOLEAN DEFAULT 0"))

        cols = conn.execute(text("PRAGMA table_info(invite_tokens)")).fetchall()
        col_names = {row[1] for row in cols}
        if col_names and "expires_at" not in col_names:
            conn.execute(text("ALTER TABLE invite_tokens ADD COLUMN expires_at DATETIME"))
        if col_names and "invitee_telegram_user_id" not in col_names:
            conn.execute(text("ALTER TABLE invite_tokens ADD COLUMN invitee_telegram_user_id INTEGER"))
        if col_names and "status" not in col_names:
            conn.execute(text("ALTER TABLE invite_tokens ADD COLUMN status VARCHAR(16)"))
        if col_names and "accepted_at" not in col_names:
            conn.execute(text("ALTER TABLE invite_tokens ADD COLUMN accepted_at DATETIME"))
        if col_names and "declined_at" not in col_names:
            conn.execute(text("ALTER TABLE invite_tokens ADD COLUMN declined_at DATETIME"))

_ensure_family_group_column()

@app.get("/health")
def health():
    return {"ok": True}
