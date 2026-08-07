"""Carga inicial de clientes a partir de dados/entregas_relatorio.csv.

Lê colunas "CNPJ Cliente" e "Cliente", normaliza CNPJ e faz upsert idempotente
por CNPJ (e-mails ficam vazios na inserção).

Uso:
  .\\.venv\\Scripts\\python.exe database/deploy/seed_clients_from_csv.py
  .\\.venv\\Scripts\\python.exe database/deploy/seed_clients_from_csv.py --dry-run
  .\\.venv\\Scripts\\python.exe database/deploy/seed_clients_from_csv.py --csv dados/entregas_relatorio.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.client_service import ClientService, ClientServiceError
from app.utils.cnpj import is_valid_cnpj, normalize_cnpj

DEFAULT_CSV = ROOT / "dados" / "entregas_relatorio.csv"
ACTOR = "seed_clients_from_csv"


def _load_unique_clients(csv_path: Path) -> OrderedDict[str, str]:
    """Map cnpj -> name (first non-empty name wins)."""
    clients: OrderedDict[str, str] = OrderedDict()
    with csv_path.open("r", encoding="latin-1", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        if not reader.fieldnames:
            raise SystemExit(f"CSV sem cabeçalho: {csv_path}")
        for row in reader:
            raw_cnpj = (row.get("CNPJ Cliente") or "").strip()
            name = (row.get("Cliente") or "").strip()
            if not raw_cnpj or not name:
                continue
            cnpj = normalize_cnpj(raw_cnpj)
            if not is_valid_cnpj(cnpj):
                continue
            if cnpj not in clients:
                clients[cnpj] = name
    return clients


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed de clientes a partir do CSV de entregas")
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Caminho do CSV (default: {DEFAULT_CSV})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Só lista o que seria feito")
    args = parser.parse_args()

    csv_path = args.csv if args.csv.is_absolute() else ROOT / args.csv
    if not csv_path.is_file():
        print(f"Arquivo não encontrado: {csv_path}", file=sys.stderr)
        return 1

    clients = _load_unique_clients(csv_path)
    print(f"Clientes distintos com CNPJ válido: {len(clients)}")

    if args.dry_run:
        for cnpj, name in list(clients.items())[:20]:
            print(f"  {cnpj}  {name}")
        if len(clients) > 20:
            print(f"  … e mais {len(clients) - 20}")
        return 0

    service = ClientService()
    inserted = 0
    updated = 0
    errors = 0
    for cnpj, name in clients.items():
        try:
            _, action = service.upsert_from_seed(name=name, cnpj_raw=cnpj, actor=ACTOR)
            if action == "inserted":
                inserted += 1
            else:
                updated += 1
        except ClientServiceError as exc:
            errors += 1
            print(f"ERRO {cnpj}: {exc}", file=sys.stderr)

    print(f"Inseridos: {inserted} | Atualizados: {updated} | Erros: {errors}")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
