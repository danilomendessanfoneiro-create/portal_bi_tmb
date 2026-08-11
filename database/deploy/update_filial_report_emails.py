"""Atualiza prb_users.report_emails das filiais a partir da lista operacional.

Uso:
  .\\.venv\\Scripts\\python.exe database/deploy/update_filial_report_emails.py --dry-run
  .\\.venv\\Scripts\\python.exe database/deploy/update_filial_report_emails.py
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.services  # noqa: F401 — evita import circular com report_emails
from app.repositories.base import get_connection
from app.repositories.user_repository import UserRepository
from app.utils.report_emails import validate_report_emails

ACTOR = "update_filial_report_emails"
EMAIL_EXTRACT_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Chave canônica (sem TMB, sem acento) -> texto bruto da lista operacional.
FILIAL_EMAILS_RAW: dict[str, str] = {
    "PATOS DE MINAS": (
        "administrativopatos@tmblogistica.com.br; antonio.alves@tmblogistica.com.br"
    ),
    "UBERLANDIA": (
        "monitoramentoub@tmblogistica.com.br; cduberlandia@tmblogistica.com.br; "
        "lucas.oliveira@tmblogistica.com.br"
    ),
    "VIANA": (
        "administrativo1@tmblogistica.com.br; agendamento.viana@tmblogistica.com.br; "
        "operacoes@tmblogistica.com.br; gerenciaes@tmblogistica.com.br; "
        "coordenacoes@tmblogistica.com.br"
    ),
    "DIVINOPOLIS": (
        "cddivinopolis1@tmblogistica.com.br; cddivinopolis@tmblogistica.com.br"
    ),
    "MACHADO": (
        "cdmachado@tmblogistica.com.br; administrativomch@tmblogistica.com.br; "
        "joao.henrique@tmblogistica.com.br; expedicaomch@tmblogistica.com.br; "
        "joao.henrique@tmblogistica.com.br; operacaomch@tmblogistica.com.br"
    ),
    "TOCANTINS": (
        "administrativouba@tmblogistica.com.br;transporteuba@tmblogistica.com.br;"
        "brendon.oliveira@tmblogistica.com.br"
    ),
    "VARGINHA": (
        'Kimberly Gabriela" <preacertovga@tmblogistica.com.br>; '
        "'Maria Eduarda' <maria.eduarda@tmblogistica.com.br>"
    ),
    "BETIM": (
        "expedicaobt@tmblogistica.com.br; transportebt@tmblogistica.com.br; "
        "transportebt1@tmblogistica.com.br; 'Jefferson Oliveira' <cdbetim@tmblogistica.com.br>; "
        "Yasmin Freitas <admbt@tmblogistica.com.br>; programacaobt@tmblogistica.com.br; "
        "expedicaobt@tmblogistica.com.br"
    ),
    "JUIZ DE FORA": "qualidadejf@tmblogistica.com.br;operacaojf@tmblogistica.com.br",
    "MONTES CLAROS": (
        "administrativo1mc@tmblogistica.com.br;administrativomc@tmblogistica.com.br;"
        "cdmontesclaros@tmblogistica.com.br"
    ),
    "ARARUAMA": (
        "cd.lagos@tmblogistica.com.br;cd.lagos2@tmblogistica.com.br;"
        "pedro.ricardo@tmblogistica.com.br"
    ),
    "DUQUE DE CAXIAS": (
        "Delson Lima' <cdcaxias@tmblogistica.com.br>; TMB <cdcaxias1@tmblogistica.com.br>; "
        "'Renato Gonçalves' <cdcaxias2@tmblogistica.com.br>; Alan <expedicaodc@tmblogistica.com.br>; "
        "cdcaxias3@tmblogistica.com.br; 'Diego Dantas' <diego.dantas@tmblogistica.com.br>"
    ),
    "GOVERNADOR VALADARES": (
        "administrativogv@tmblogistica.com.br;operacaogv@tmblogistica.com.br;"
        "CD Valadares <cdvaladares@tmblogistica.com.br>"
    ),
}

BRANCH_ALIASES = {
    "D DE CAXIAS": "DUQUE DE CAXIAS",
    "DUQUE DE CAXIAS": "DUQUE DE CAXIAS",
    "VALADARES": "GOVERNADOR VALADARES",
    "GOVERNADOR VALADARES": "GOVERNADOR VALADARES",
}


def strip_accents(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def canonical_branch(name: str) -> str:
    text = strip_accents(name or "").upper()
    text = text.replace(".", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^TMB\s+", "", text)
    return BRANCH_ALIASES.get(text, text)


def extract_emails(raw: str) -> list[str]:
    seen: set[str] = set()
    emails: list[str] = []
    for match in EMAIL_EXTRACT_RE.findall(raw or ""):
        email = match.strip().rstrip(".,;").lower()
        if email in seen:
            continue
        seen.add(email)
        emails.append(email)
    return emails


def main() -> int:
    parser = argparse.ArgumentParser(description="Atualiza e-mails de relatório das filiais")
    parser.add_argument("--dry-run", action="store_true", help="Só lista o que seria gravado")
    args = parser.parse_args()

    expected: dict[str, str] = {}
    for key, raw in FILIAL_EMAILS_RAW.items():
        emails = extract_emails(raw)
        if not emails:
            print(f"ERRO: nenhum e-mail extraído para {key}", file=sys.stderr)
            return 1
        expected[key] = ";".join(validate_report_emails(";".join(emails)))

    repo = UserRepository()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id FROM prb_users
            WHERE lower(profile) = 'filial'
              AND COALESCE(TRIM(branch), '') <> ''
            ORDER BY branch, login
            """
        ).fetchall()
    users = [
        user
        for row in rows
        if (user := repo.get_by_id(int(row["id"]), include_disabled=True)) is not None
    ]

    matched_keys: set[str] = set()
    updated = 0
    unchanged = 0
    missing_users = 0

    for user in users:
        key = canonical_branch(user.branch or "")
        if key not in expected:
            print(f"SKIP {user.login} branch={user.branch!r} (sem lista nova)")
            continue
        matched_keys.add(key)
        new_value = expected[key]
        old_value = (user.report_emails or "").strip() or None
        if old_value == new_value:
            print(f"OK   {user.login} ({user.branch}) já está atualizado ({len(new_value.split(';'))} e-mails)")
            unchanged += 1
            continue
        print(f"{'DRY ' if args.dry_run else 'UPD '}{user.login} ({user.branch})")
        print(f"     de: {old_value or '(vazio)'}")
        print(f"     para: {new_value}")
        if not args.dry_run:
            repo.update(user.id, {"report_emails": new_value}, ACTOR)
        updated += 1

    for key in expected:
        if key not in matched_keys:
            print(f"AUSENTE no cadastro: {key}", file=sys.stderr)
            missing_users += 1

    print(
        f"Pronto. atualizados={updated} iguais={unchanged} "
        f"filiais_sem_usuario={missing_users} dry_run={args.dry_run}"
    )
    return 1 if missing_users else 0


if __name__ == "__main__":
    raise SystemExit(main())
