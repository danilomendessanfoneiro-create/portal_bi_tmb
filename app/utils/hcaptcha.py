"""hCaptcha server-side verification."""

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger("hcaptcha")

VERIFY_URL = "https://api.hcaptcha.com/siteverify"


class HCaptchaError(Exception):
    pass


def hcaptcha_enabled() -> bool:
    flag = (os.getenv("HCAPTCHA_ENABLED") or "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    secret = (os.getenv("HCAPTCHA_SECRET") or "").strip()
    sitekey = (os.getenv("HCAPTCHA_SITEKEY") or "").strip()
    return bool(secret and sitekey)


def verify_hcaptcha(token: Optional[str], *, remote_ip: Optional[str] = None) -> None:
    """Valida o token do widget. Levanta HCaptchaError se inválido."""
    if not hcaptcha_enabled():
        return

    response_token = (token or "").strip()
    if not response_token:
        raise HCaptchaError("Complete o desafio hCaptcha.")

    data = {
        "secret": settings.hcaptcha_secret.strip(),
        "response": response_token,
    }
    if remote_ip:
        data["remoteip"] = remote_ip

    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.post(VERIFY_URL, data=data)
            payload = res.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Falha ao contatar hCaptcha: %s", exc)
        raise HCaptchaError("Não foi possível validar o hCaptcha. Tente novamente.") from exc

    if not payload.get("success"):
        codes = payload.get("error-codes") or []
        logger.info("hCaptcha rejeitado: %s", codes)
        raise HCaptchaError("hCaptcha inválido ou expirado. Tente novamente.")
