"""Ponte temporária: SMTP operacional via Gmail até o mail TMB aceitar a VPS.

Usa TECH_SMTP_* do .env (mesma conta do monitoramento) só para autenticar.
O From dos relatórios permanece gestaoentregas@tmblogistica.com.br.
O monitoramento técnico (TECH_SMTP_TO) não é alterado.

Uso na VPS:
  sudo -u www-data /opt/portal-bi-tmb/.venv/bin/python database/deploy/switch_smtp_gmail_bridge.py
  sudo -u www-data /opt/portal-bi-tmb/.venv/bin/python database/deploy/switch_smtp_gmail_bridge.py --revert
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.schemas.settings import SmtpCreate, SmtpFilter, SmtpUpdate
from app.services.smtp_service import SmtpSettingsService

GMAIL_NAME = "gmail-temporario"
TMB_HOST = "mail.tmblogistica.com.br"
GMAIL_HOST = "smtp.gmail.com"
SENDER_EMAIL = "gestaoentregas@tmblogistica.com.br"
SENDER_NAME = "Gestao Entregas TMB"
ACTOR = "ops-gmail-bridge"


def _items(svc: SmtpSettingsService):
    rows, _ = svc.list(SmtpFilter(enabled=None, page_size=100, sort_by="id"))
    return rows


def _find(rows, *, name: str | None = None, host: str | None = None):
    for item in rows:
        if name and item.name == name:
            return item
        if host and (item.host or "").lower() == host.lower():
            return item
    return None


def apply_bridge(svc: SmtpSettingsService) -> None:
    user = (os.getenv("TECH_SMTP_USER") or "").strip()
    password = (os.getenv("TECH_SMTP_PASSWORD") or "").strip()
    if not user or not password:
        raise SystemExit("TECH_SMTP_USER / TECH_SMTP_PASSWORD vazios no .env")

    rows = _items(svc)
    tmb = _find(rows, host=TMB_HOST)
    if tmb and tmb.is_default:
        svc.update(tmb.id, SmtpUpdate(is_default=False), ACTOR)
        print(f"tmb id={tmb.id} is_default=false (config preservada)")

    gmail = _find(rows, name=GMAIL_NAME) or _find(rows, host=GMAIL_HOST)
    if gmail:
        svc.update(
            gmail.id,
            SmtpUpdate(
                name=GMAIL_NAME,
                host=GMAIL_HOST,
                port=587,
                username=user,
                password=password,
                use_tls=True,
                sender_email=SENDER_EMAIL,
                sender_name=SENDER_NAME,
                timeout_seconds=30,
                enabled=True,
                is_default=True,
            ),
            ACTOR,
        )
        print(f"gmail id={gmail.id} atualizado e marcado como padrão")
        return

    created = svc.create(
        SmtpCreate(
            name=GMAIL_NAME,
            host=GMAIL_HOST,
            port=587,
            username=user,
            password=password,
            use_tls=True,
            sender_email=SENDER_EMAIL,
            sender_name=SENDER_NAME,
            timeout_seconds=30,
            is_default=True,
            enabled=True,
        ),
        ACTOR,
    )
    print(f"gmail id={created.id} criado e marcado como padrão")


def revert_bridge(svc: SmtpSettingsService) -> None:
    rows = _items(svc)
    tmb = _find(rows, host=TMB_HOST)
    gmail = _find(rows, name=GMAIL_NAME) or _find(rows, host=GMAIL_HOST)
    if tmb is None:
        raise SystemExit("Config mail.tmblogistica.com.br não encontrada para reverter")
    if gmail and gmail.is_default:
        svc.update(gmail.id, SmtpUpdate(is_default=False, enabled=True), ACTOR)
        print(f"gmail id={gmail.id} is_default=false")
    svc.update(tmb.id, SmtpUpdate(enabled=True, is_default=True), ACTOR)
    print(f"tmb id={tmb.id} restaurado como padrão")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revert", action="store_true")
    args = parser.parse_args()
    svc = SmtpSettingsService()
    if args.revert:
        revert_bridge(svc)
    else:
        apply_bridge(svc)
    rows = _items(svc)
    for item in rows:
        print(
            f"  id={item.id} name={item.name} host={item.host}:{item.port} "
            f"from={item.sender_email} default={item.is_default} enabled={item.enabled}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
