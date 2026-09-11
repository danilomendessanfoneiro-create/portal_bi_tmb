"""Cadastra a filial TMB BARRA MANSA (usuário perfil filial) para validação de importação.

A planilha TMS traz a sigla exatamente como "TMB BARRA MANSA" (sem "DO").
O campo branch precisa bater 100% com essa string, senão a importação bloqueia.

Padrão idêntico a seed_filiais_faltantes_import.py / migration 003.

Uso (local):
  .\\.venv\\Scripts\\python.exe database/deploy/seed_filial_barra_mansa.py --dry-run
  .\\.venv\\Scripts\\python.exe database/deploy/seed_filial_barra_mansa.py

Uso (VPS, só se autorizado):
  cd /opt/portal-bi-tmb && .venv/bin/python database/deploy/seed_filial_barra_mansa.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.repositories.base import get_connection
from app.utils.password import hash_password

# Mesma senha padrão das filiais do seed 003 / seed_filiais_faltantes_import.
DEFAULT_PASSWORD = "tmb123"

# login, branch (exato da planilha), display_name/name
FILIAL = ("barramansa", "TMB BARRA MANSA", "TMB Barra Mansa")
ACTOR = "seed_filial_barra_mansa"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed usuário filial TMB BARRA MANSA para importação"
    )
    parser.add_argument("--dry-run", action="store_true", help="Só mostra o que seria feito")
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help=f"Senha inicial (default: {DEFAULT_PASSWORD})",
    )
    parser.add_argument(
        "--branch",
        default=FILIAL[1],
        help=f'Sigla exata da planilha (default: "{FILIAL[1]}")',
    )
    parser.add_argument(
        "--report-emails",
        default="",
        help="E-mails do relatório separados por ; (opcional)",
    )
    args = parser.parse_args()

    login, _branch_default, display = FILIAL
    branch = (args.branch or "").strip()
    report_emails = (args.report_emails or "").strip() or None
    pwd_hash = hash_password(args.password)

    with get_connection() as conn:
        existing_branches = {
            str(r["branch"]).strip()
            for r in conn.execute(
                """
                SELECT DISTINCT TRIM(branch) AS branch
                FROM prb_users
                WHERE enabled = TRUE
                  AND lower(profile) = 'filial'
                  AND branch IS NOT NULL
                  AND TRIM(branch) <> ''
                """
            ).fetchall()
            if r.get("branch")
        }
        row_login = conn.execute(
            "SELECT id, login, branch, enabled FROM prb_users WHERE lower(login) = %s",
            [login],
        ).fetchone()

        if branch in existing_branches:
            print(f"SKIP branch já cadastrada: {branch}")
            return 0

        if row_login:
            print(
                f"UPDATE login={login} id={row_login['id']} "
                f"branch={row_login['branch']!r} -> {branch!r}"
            )
            if args.dry_run:
                return 0
            conn.execute(
                """
                UPDATE prb_users
                SET profile = 'filial',
                    branch = %s,
                    display_name = COALESCE(NULLIF(TRIM(display_name), ''), %s),
                    name = COALESCE(NULLIF(TRIM(name), ''), %s),
                    report_emails = COALESCE(%s, report_emails),
                    enabled = TRUE,
                    modified_by = %s,
                    modified_on = NOW()
                WHERE lower(login) = %s
                """,
                [branch, display, display, report_emails, ACTOR, login],
            )
            print("OK atualizado.")
            return 0

        print(f"INSERT {login} -> {branch} ({display})")
        if args.dry_run:
            return 0

        conn.execute(
            """
            INSERT INTO prb_users (
                login, password_hash, profile, branch, display_name, name, code,
                report_emails,
                created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, %s, 'filial', %s, %s, %s, %s,
                %s,
                %s, NOW(), %s, NOW(), TRUE
            )
            """,
            [
                login,
                pwd_hash,
                branch,
                display,
                display,
                login,
                report_emails,
                ACTOR,
                ACTOR,
            ],
        )
        print(f"OK criado. Senha inicial: {args.password}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
