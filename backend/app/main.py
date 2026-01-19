from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routers import auth, profile, event_info, admin, temp_profile

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

@app.get("/health")
def health():
    return {"ok": True}
