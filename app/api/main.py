"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import api_integration, auth, imports, recipients, schedules, smtp, users
from app.config import settings

app = FastAPI(
    title="Portal BI TMB API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

origins = {
    settings.public_origin,
    settings.admin_public_url,
    settings.bi_public_url,
    "http://localhost:5173",
    "http://localhost:8501",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8501",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(smtp.router, prefix="/api")
app.include_router(recipients.router, prefix="/api")
app.include_router(schedules.router, prefix="/api")
app.include_router(api_integration.router, prefix="/api")
app.include_router(imports.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
