"""
Gera snapshots fake dos últimos N dias para demo do BI Histórico.

Uso:
    python database/deploy/seed_bi_snapshot_demo.py
    python database/deploy/seed_bi_snapshot_demo.py --days 30 --replace-demo
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.repositories.base import get_connection
from app.repositories.bi_snapshot_repository import BiSnapshotRepository
from app.services.bi_snapshot_service import BiSnapshotService


def _sample_dims() -> tuple[list[str], list[str], list[str]]:
    filiais = ["TMB VIANA", "TMB BETIM", "TMB TOCANTINS", "TMB VARGINHA", "TMB JUNDIAI"]
    clientes = ["CLIENTE DEMO A", "CLIENTE DEMO B", "CLIENTE DEMO C", "CLIENTE DEMO D"]
    cidades = ["Vitória", "Betim", "Palmas", "Varginha", "Jundiaí"]
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT filial, cliente, cidade_entrega
                FROM prb_deliveries
                WHERE enabled = TRUE
                  AND filial IS NOT NULL
                LIMIT 200
                """
            ).fetchall()
        if rows:
            filiais = sorted({r["filial"] for r in rows if r["filial"]})[:12] or filiais
            clientes = sorted({r["cliente"] for r in rows if r["cliente"]})[:20] or clientes
            cidades = sorted({r["cidade_entrega"] for r in rows if r["cidade_entrega"]})[:20] or cidades
    except Exception:
        pass
    return filiais, clientes, cidades


def _fake_day(business_date: date, n: int, filiais, clientes, cidades) -> pd.DataFrame:
    rows = []
    for i in range(n):
        remessa = f"DEMO-{business_date:%Y%m%d}-{i+1:04d}"
        rows.append(
            {
                "remessa_numero": remessa,
                "nro_entrega": remessa,
                "nota_fiscal": f"NF{100000 + i}",
                "filial": random.choice(filiais),
                "cliente": random.choice(clientes),
                "cidade_entrega": random.choice(cidades),
                "uf_entrega": "MG",
                "status": "Em trânsito",
                "motorista": "DEMO MOTORISTA",
                "dias_atraso": random.randint(1, 12),
                "valor_total": round(random.uniform(80, 2500), 2),
                "prazo_considerado": datetime.combine(
                    business_date - timedelta(days=random.randint(1, 5)),
                    datetime.min.time(),
                ),
                "status_prazo": "01_ATRASO",
            }
        )
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed demo de snapshots BI histórico")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument(
        "--replace-demo",
        action="store_true",
        help="Apaga apenas snapshots source=seed-demo antes de regenerar",
    )
    args = parser.parse_args(argv)

    repo = BiSnapshotRepository()
    svc = BiSnapshotService(repo)
    if args.replace_demo:
        deleted = repo.delete_demo_runs()
        print(f"Removidos {deleted} run(s) seed-demo")

    filiais, clientes, cidades = _sample_dims()
    today = date.today()
    # tendência levemente decrescente para demo visual
    base = 140
    created = skipped = 0
    for offset in range(args.days - 1, -1, -1):
        day = today - timedelta(days=offset)
        noise = random.randint(-8, 8)
        trend = int((args.days - 1 - offset) * 0.6)
        n = max(40, base - trend + noise)
        df = _fake_day(day, n, filiais, clientes, cidades)
        result = svc.capture_if_absent(
            day,
            df,
            actor="seed-demo",
            source="seed-demo",
            source_job_id="seed_bi_snapshot_demo",
            captured_on=datetime.combine(day, datetime.min.time()).replace(hour=6, minute=30),
        )
        if result.status == "created":
            created += 1
            print(f"OK  {day} -> {result.rows} atrasos")
        elif result.status == "skipped":
            skipped += 1
            print(f"SKIP {day} (ja existe)")
        else:
            print(f"FAIL {day}: {result.message}")
            return 1

    print(f"Concluído: created={created} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
