from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .db import Base, engine
from .routers import auth, profile, event_info, admin, temp_profile, family, questions

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
app.include_router(admin.router)
app.include_router(temp_profile.router)
app.include_router(family.router)
app.include_router(questions.router)

def _ensure_family_group_column():
    if not engine.url.get_backend_name().startswith("sqlite"):
        return
    with engine.begin() as conn:
        cols = conn.execute(text("PRAGMA table_info(guests)")).fetchall()
        col_names = {row[1] for row in cols}
        if "family_group_id" not in col_names:
            conn.execute(text("ALTER TABLE guests ADD COLUMN family_group_id INTEGER"))

        cols = conn.execute(text("PRAGMA table_info(invite_tokens)")).fetchall()
        col_names = {row[1] for row in cols}
        if col_names and "expires_at" not in col_names:
            conn.execute(text("ALTER TABLE invite_tokens ADD COLUMN expires_at DATETIME"))

_ensure_family_group_column()

@app.get("/health")
def health():
    return {"ok": True}
