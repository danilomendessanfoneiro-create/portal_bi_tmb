from __future__ import annotations

import pandas as pd

from app.utils.bi_cliente_industria import (
    apply_cliente_industria_filter,
    industria_dim_col,
    unique_cliente_industria,
)


def test_unique_cliente_industria_uses_conta_not_destinatario():
    df = pd.DataFrame(
        {
            "cliente": ["14071610 EDINEUZA", "22.331.558 AMANDA"],
            "cliente_conta": ["NINFA", "STELLA DORO"],
        }
    )
    assert unique_cliente_industria(df) == ["NINFA", "STELLA DORO"]


def test_apply_cliente_industria_filter():
    df = pd.DataFrame(
        {
            "cliente": ["DEST A", "DEST B"],
            "cliente_conta": ["NINFA", "STELLA DORO"],
        }
    )
    out = apply_cliente_industria_filter(df, ["NINFA"])
    assert list(out["cliente"]) == ["DEST A"]


def test_industria_dim_col_prefers_conta():
    df = pd.DataFrame({"cliente": ["A"], "cliente_conta": ["NINFA"]})
    assert industria_dim_col(df) == "cliente_conta"


def test_migration_046_adds_cliente_conta():
    from pathlib import Path

    sql = (
        Path(__file__).resolve().parents[1]
        / "database"
        / "migrations"
        / "046_add_snapshot_cliente_conta.sql"
    ).read_text(encoding="utf-8")
    assert "prb_bi_snapshot_overdue" in sql
    assert "prb_progress_snapshot_item" in sql
    assert "ADD COLUMN IF NOT EXISTS cliente_conta" in sql
