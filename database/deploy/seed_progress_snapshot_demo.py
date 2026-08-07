"""
Gera snapshots fake de Progressão para a semana corrente (seg→sex).

Cria import batches sintéticos + prb_progress_snapshot_* com captured_at
nos dias úteis, para o gráfico da aba Progressão.

Uso:
  .\\.venv\\Scripts\\python.exe database/deploy/seed_progress_snapshot_demo.py
  .\\.venv\\Scripts\\python.exe database/deploy/seed_progress_snapshot_demo.py --replace
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.repositories.base import get_connection
from app.services.progress_snapshot_service import ProgressSnapshotService

ACTOR = "seed_progress_demo"
FILE_PREFIX = "DEMO-PROGRESS-"
TZ = ZoneInfo("America/Sao_Paulo")

STATUSES = [
    "EM ROTA",
    "PENDENTE",
    "AGENDADO",
    "EM TRANSFERENCIA",
    "DISPONIVEL PARA ENTREGA",
]


def _weekdays_mon_to_today(today: date) -> list[date]:
    """Segunda da semana até hoje (máx. sexta)."""
    monday = today - timedelta(days=today.weekday())
    end = min(today, monday + timedelta(days=4))
    out: list[date] = []
    d = monday
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def _sample_dims() -> tuple[list[str], list[str], list[str], list[str]]:
    filiais = ["TMB VIANA", "TMB BETIM", "TMB TOCANTINS", "TMB VARGINHA", "TMB JUNDIAI"]
    clientes = ["CLIENTE DEMO A", "CLIENTE DEMO B", "CLIENTE DEMO C", "CLIENTE DEMO D"]
    cidades = ["Vitória", "Betim", "Palmas", "Varginha", "Jundiaí"]
    cnpjs = ["07604556000136", "60746948000112", "33000167000101"]
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT filial, cliente, cidade_entrega, cnpj_cliente
                FROM prb_deliveries
                WHERE enabled = TRUE
                LIMIT 300
                """
            ).fetchall()
        if rows:
            filiais = sorted({r["filial"] for r in rows if r.get("filial")})[:12] or filiais
            clientes = sorted({r["cliente"] for r in rows if r.get("cliente")})[:20] or clientes
            cidades = (
                sorted({r["cidade_entrega"] for r in rows if r.get("cidade_entrega")})[:20]
                or cidades
            )
            found = sorted(
                {str(r["cnpj_cliente"]) for r in rows if r.get("cnpj_cliente")}
            )[:20]
            if found:
                cnpjs = found
    except Exception:
        pass
    return filiais, clientes, cidades, cnpjs


def _delete_previous_demo() -> tuple[int, int]:
    """Remove runs + batches anteriores deste seed. Retorna (runs, batches)."""
    with get_connection() as conn:
        batch_ids = [
            int(r["id"])
            for r in conn.execute(
                """
                SELECT id FROM prb_import_batches
                WHERE created_by = %s AND file_name LIKE %s
                """,
                [ACTOR, f"{FILE_PREFIX}%"],
            ).fetchall()
        ]
        if not batch_ids:
            return 0, 0
        runs = conn.execute(
            """
            DELETE FROM prb_progress_snapshot_run
            WHERE import_batch_id = ANY(%s)
            RETURNING id
            """,
            [batch_ids],
        ).fetchall()
        batches = conn.execute(
            """
            DELETE FROM prb_import_batches
            WHERE id = ANY(%s)
            RETURNING id
            """,
            [batch_ids],
        ).fetchall()
    return len(runs), len(batches)


def _create_batch(*, day: date, row_count: int) -> int:
    name = f"{FILE_PREFIX}{day:%Y%m%d}.csv"
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO prb_import_batches (
                file_name, file_ext, file_size_bytes, file_path, file_mtime,
                status, total_rows, valid_rows, error_rows, rows_processed,
                rows_inserted, rows_updated, progress_pct,
                started_on, finished_on, duration_ms,
                created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, 'csv', 1024, %s, %s,
                'imported', %s, %s, 0, %s,
                %s, 0, 100,
                %s, %s, 1500,
                %s, NOW(), %s, NOW(), TRUE
            )
            RETURNING id
            """,
            [
                name,
                f"/demo/{name}",
                datetime.combine(day, time(9, 0)),
                row_count,
                row_count,
                row_count,
                row_count,
                datetime.combine(day, time(9, 55)),
                datetime.combine(day, time(10, 0)),
                ACTOR,
                ACTOR,
            ],
        ).fetchone()
    return int(row["id"])


def _build_pool(
    *,
    size: int,
    filiais: list[str],
    clientes: list[str],
    cidades: list[str],
    cnpjs: list[str],
) -> list[dict[str, Any]]:
    """prazo_offset relativo ao dia do upload → vira dt_prazo_atual na captura."""
    # Pesos: mais atrasos no início da semana para o gráfico de STATUS PRAZO
    offsets = [-3, -2, -1, 0, 0, 1, 2, 5]
    pool: list[dict[str, Any]] = []
    for i in range(size):
        nro = f"PROG-DEMO-{i + 1:04d}"
        pool.append(
            {
                "nro_entrega": nro,
                "remessa_numero": nro,
                "status": random.choice(STATUSES),
                "prazo_offset": offsets[i % len(offsets)],
                "filial": random.choice(filiais),
                "cliente": random.choice(clientes),
                "cnpj_cliente": random.choice(cnpjs),
                "cidade_entrega": random.choice(cidades),
                "uf_entrega": "MG",
                "motorista": f"MOTORISTA {(i % 8) + 1}",
                "valor_total": round(random.uniform(50, 1800), 2),
            }
        )
    return pool


def _rows_for_day(active: list[dict[str, Any]], day: date) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in active:
        copy = {k: v for k, v in row.items() if k != "prazo_offset"}
        offset = int(row.get("prazo_offset", 0))
        copy["dt_prazo_atual"] = day + timedelta(days=offset)
        out.append(copy)
    return out


def _evolve(
    active: list[dict[str, Any]],
    *,
    deliver_n: int,
    reshuffle_pct: float = 0.25,
) -> list[dict[str, Any]]:
    """Remove N entregas (viram Pedidos Entregues) e muda status/prazo de parte do restante."""
    if deliver_n <= 0 or not active:
        remaining = list(active)
    else:
        deliver_n = min(deliver_n, len(active))
        idxs = set(random.sample(range(len(active)), deliver_n))
        remaining = [row for i, row in enumerate(active) if i not in idxs]

    offsets = [-3, -2, -1, 0, 1, 2, 5]
    out: list[dict[str, Any]] = []
    for row in remaining:
        copy = dict(row)
        if random.random() < reshuffle_pct:
            copy["status"] = random.choice(STATUSES)
            copy["prazo_offset"] = random.choice(offsets)
        out.append(copy)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed demo Progressão (semana seg→sex)")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Apaga batches/snapshots anteriores deste seed antes de regenerar",
    )
    parser.add_argument(
        "--base",
        type=int,
        default=120,
        help="Quantidade inicial de pedidos na segunda (default 120)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed para reprodutibilidade",
    )
    args = parser.parse_args(argv)
    random.seed(args.seed)

    today = date.today()
    days = _weekdays_mon_to_today(today)
    if not days:
        print("Sem dias úteis para seed.", file=sys.stderr)
        return 1

    if args.replace:
        n_runs, n_batches = _delete_previous_demo()
        print(f"Removidos: {n_runs} snapshot(s), {n_batches} batch(es) demo")

    filiais, clientes, cidades, cnpjs = _sample_dims()
    active = _build_pool(
        size=args.base,
        filiais=filiais,
        clientes=clientes,
        cidades=cidades,
        cnpjs=cnpjs,
    )
    svc = ProgressSnapshotService()

    # Entregas por dia (anti-join): ~8–15% do volume do dia anterior
    deliver_plan = [0, 14, 12, 10, 9]

    print(f"Semana {days[0]} -> {days[-1]} ({len(days)} upload(s))")
    for i, day in enumerate(days):
        if i > 0:
            deliver_n = deliver_plan[i] if i < len(deliver_plan) else max(5, len(active) // 10)
            active = _evolve(active, deliver_n=deliver_n)

        batch_id = _create_batch(day=day, row_count=len(active))
        captured_at = datetime.combine(day, time(10, 0), tzinfo=TZ)
        result = svc.capture_for_batch(
            batch_id,
            _rows_for_day(active, day),
            actor=ACTOR,
            notes=f"seed demo progressao {day.isoformat()}",
            captured_at=captured_at,
            replace=True,
        )
        if result.status in {"created", "replaced"}:
            approx = deliver_plan[i] if i else 0
            print(
                f"OK  {day} batch={batch_id} run={result.run_id} "
                f"linhas={result.rows} (entregues no dia~={approx})"
            )
        else:
            print(f"FAIL {day}: {result.status} {result.message}", file=sys.stderr)
            return 1

    print(
        "Concluido. Abra o BI -> Progressao (janela 7 dias) para ver o grafico. "
        "Pedidos Entregues = nro_entrega sumiu entre uploads consecutivos."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
