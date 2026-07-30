"""Cadastra usuários perfil filial ausentes na validação de importação manual.

Filiais reportadas na planilha e ainda sem registro em prb_users:
  TMB ARARUAMA, TMB DIVINOPOLIS, TMB UBERLÂNDIA, TMB MACHADO,
  TMB JUIZ DE FORA, TMB VALADARES

Uso:
  .\\.venv\\Scripts\\python.exe database/deploy/seed_filiais_faltantes_import.py
  .\\.venv\\Scripts\\python.exe database/deploy/seed_filiais_faltantes_import.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.repositories.base import get_connection
from app.utils.password import hash_password

# Mesma senha padrão das filiais do seed 003 (hash legado compartilhado).
DEFAULT_PASSWORD = "tmb123"

FILIAIS = [
    ("araruama", "TMB ARARUAMA", "TMB Araruama"),
    ("divinopolis", "TMB DIVINOPOLIS", "TMB Divinópolis"),
    ("uberlandia", "TMB UBERLÂNDIA", "TMB Uberlândia"),
    ("machado", "TMB MACHADO", "TMB Machado"),
    ("juizdefora", "TMB JUIZ DE FORA", "TMB Juiz de Fora"),
    ("valadares", "TMB VALADARES", "TMB Valadares"),
]


def _slug(login: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", login.lower())


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed filiais faltantes para importação")
    parser.add_argument("--dry-run", action="store_true", help="Só lista o que seria feito")
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help=f"Senha inicial dos usuários novos (default: {DEFAULT_PASSWORD})",
    )
    args = parser.parse_args()
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
        existing_logins = {
            str(r["login"]).strip().lower()
            for r in conn.execute("SELECT login FROM prb_users").fetchall()
        }

        created = 0
        skipped = 0
        for login, branch, display in FILIAIS:
            login = _slug(login)
            if branch in existing_branches:
                print(f"SKIP branch já cadastrada: {branch}")
                skipped += 1
                continue
            if login in existing_logins:
                print(f"SKIP login já existe ({login}) — atualizando branch/enabled se preciso")
                if args.dry_run:
                    continue
                conn.execute(
                    """
                    UPDATE prb_users
                    SET profile = 'filial',
                        branch = %s,
                        display_name = COALESCE(NULLIF(TRIM(display_name), ''), %s),
                        name = COALESCE(NULLIF(TRIM(name), ''), %s),
                        enabled = TRUE,
                        modified_by = 'seed_filiais_faltantes',
                        modified_on = NOW()
                    WHERE lower(login) = %s
                    """,
                    [branch, display, display, login],
                )
                created += 1
                continue

            print(f"INSERT {login} -> {branch}")
            if args.dry_run:
                created += 1
                continue
            conn.execute(
                """
                INSERT INTO prb_users (
                    login, password_hash, profile, branch, display_name, name, code,
                    created_by, created_on, modified_by, modified_on, enabled
                ) VALUES (
                    %s, %s, 'filial', %s, %s, %s, %s,
                    'seed_filiais_faltantes', NOW(), 'seed_filiais_faltantes', NOW(), TRUE
                )
                """,
                [login, pwd_hash, branch, display, display, login],
            )
            created += 1

    print(f"Pronto. criados/atualizados={created} ignorados={skipped} dry_run={args.dry_run}")
    if not args.dry_run:
        print(f"Senha inicial dos novos logins: {args.password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
