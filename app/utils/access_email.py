"""E-mail bodies for access / provisional password."""

from __future__ import annotations

from app.config import settings

PROVISIONAL_PASSWORD_HOURS = 24


def build_provisional_access_email(
    *,
    display_name: str | None,
    login: str,
    provisional_password: str,
) -> tuple[str, str]:
    name = (display_name or login or "usuário").strip() or "usuário"
    access_link = (settings.admin_public_url or settings.public_origin).rstrip("/") + "/login"
    text = (
        f"Olá, {name}.\n\n"
        "Uma senha provisória foi gerada para sua conta no Portal BI TMB Logística.\n\n"
        f"Usuário (login): {login}\n"
        f"Senha provisória: {provisional_password}\n\n"
        f"Acesse: {access_link}\n\n"
        f"Esta senha é válida por {PROVISIONAL_PASSWORD_HOURS} horas. "
        "No primeiro acesso, você deverá cadastrar uma nova senha definitiva.\n"
    )
    html = (
        f"<p>Olá, <strong>{name}</strong>.</p>"
        "<p>Uma senha provisória foi gerada para sua conta no "
        "<strong>Portal BI TMB Logística</strong>.</p>"
        f"<p><strong>Usuário (login):</strong> <code>{login}</code></p>"
        f"<p><strong>Senha provisória:</strong> <code>{provisional_password}</code></p>"
        f'<p>Acesse: <a href="{access_link}">{access_link}</a></p>'
        f"<p>Esta senha é válida por <strong>{PROVISIONAL_PASSWORD_HOURS} horas</strong>. "
        "No primeiro acesso, você deverá cadastrar uma nova senha definitiva.</p>"
    )
    return text, html
