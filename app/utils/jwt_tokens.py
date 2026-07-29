"""JWT helpers for unified auth (API + Streamlit)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt

from app.config import settings
from app.models import User


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user.login,
        "uid": user.id,
        "profile": user.profile,
        "branch": user.branch,
        "name": user.display_name or user.name or user.login,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
