"""
Run incremental SQL migrations in order.

Usage (from project root):
    python database/deploy/run_migrations.py
    python database/deploy/run_migrations.py --database-url "postgresql://..."
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402


def ensure_schema(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prb_schema_migrations (
            id          SERIAL PRIMARY KEY,
            filename    VARCHAR(255) NOT NULL UNIQUE,
            applied_on  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            created_by  VARCHAR(100) DEFAULT 'deploy',
            created_on  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            modified_by VARCHAR(100) DEFAULT 'deploy',
            modified_on TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            enabled     BOOLEAN NOT NULL DEFAULT TRUE
        )
        """
    )


def applied_files(conn: psycopg.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT filename FROM prb_schema_migrations WHERE enabled = TRUE"
    ).fetchall()
    return {r[0] if not isinstance(r, dict) else r["filename"] for r in rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Portal BI SQL migrations")
    parser.add_argument("--database-url", default=settings.database_url)
    args = parser.parse_args()

    migrations_dir = settings.migrations_dir
    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        print(f"No migrations found in {migrations_dir}")
        return 1

    with psycopg.connect(args.database_url) as conn:
        ensure_schema(conn)
        done = applied_files(conn)
        for path in files:
            if path.name in done:
                print(f"SKIP  {path.name}")
                continue
            sql = path.read_text(encoding="utf-8")
            print(f"APPLY {path.name} ...", end=" ", flush=True)
            conn.execute(sql)
            conn.execute(
                "INSERT INTO prb_schema_migrations (filename) VALUES (%s)",
                (path.name,),
            )
            conn.commit()
            print("OK")

    print("Migrations finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
