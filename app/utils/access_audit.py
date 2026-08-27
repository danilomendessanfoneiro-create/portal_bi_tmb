"""Lightweight audit log for access/password operations (no secrets)."""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("portal_bi.access_audit")


def audit_access_event(
    action: str,
    *,
    actor: Optional[str] = None,
    target_user_id: Optional[int] = None,
    detail: Optional[str] = None,
) -> None:
    payload: dict[str, Any] = {"action": action}
    if actor:
        payload["actor"] = actor
    if target_user_id is not None:
        payload["target_user_id"] = target_user_id
    if detail:
        payload["detail"] = detail
    logger.info("access_audit %s", payload)
