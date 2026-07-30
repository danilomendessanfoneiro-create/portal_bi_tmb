"""
Migra entregas do CSV da planilha para prb_deliveries.

Uso:
    python database/deploy/migrate_csv_to_deliveries.py
    python database/deploy/migrate_csv_to_deliveries.py --dry-run
    python database/deploy/migrate_csv_to_deliveries.py --no-replace
    python database/deploy/migrate_csv_to_deliveries.py --csv caminho/arquivo.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.services.csv_delivery_import_service import CsvDeliveryImportService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migra CSV da planilha para prb_deliveries")
    parser.add_argument("--csv", dest="csv_path", help="Caminho do CSV (default: dados/entregas_relatorio.csv)")
    parser.add_argument("--dry-run", action="store_true", help="Só lê e mapeia, sem gravar")
    parser.add_argument(
        "--no-replace",
        action="store_true",
        help="Não apaga prb_deliveries antes; faz upsert",
    )
    args = parser.parse_args(argv)

    result = CsvDeliveryImportService().run(
        csv_path=Path(args.csv_path) if args.csv_path else None,
        replace=not args.no_replace,
        dry_run=bool(args.dry_run),
        actor="csv-migrate",
    )
    print(result.message)
    print(
        f"read={result.rows_read} inserted={result.rows_inserted} "
        f"updated={result.rows_updated} deleted={result.rows_deleted}"
    )
    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
