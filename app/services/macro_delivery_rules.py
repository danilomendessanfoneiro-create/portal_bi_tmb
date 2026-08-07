"""Regras de negócio espelhadas de calcConsolidada.vb (fonte única)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Union

import numpy as np
import pandas as pd

RULE_VERSION = "calc-consolidada-v1"

STATUS_PRAZO_ATRASO = "01_ATRASO"
STATUS_PRAZO_VENCENDO_HOJE = "02_VENCENDO HOJE"
STATUS_PRAZO_VENCENDO_AMANHA = "03_VENCENDO AMANHÃ"
STATUS_PRAZO_DEPOIS_AMANHA = "04_DEPOIS DE AMANHÃ"
STATUS_PRAZO_FUTURO = "05_VENCIMENTO FUTURO"

STATUS_ENTREGUE = "ENTREGUE"

DateLike = Union[date, datetime, pd.Timestamp, None]


def _as_date(value: DateLike) -> Optional[date]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.date()
    if isinstance(value, date):
        return value
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.date()


def classificar_status_prazo(dt_prazo_atual: DateLike, hoje: DateLike) -> str:
    """calcConsolidada: Select Case em Dt. Prazo Atual vs Date."""
    prazo = _as_date(dt_prazo_atual)
    ref = _as_date(hoje)
    if prazo is None or ref is None:
        return ""
    if prazo < ref:
        return STATUS_PRAZO_ATRASO
    if prazo == ref:
        return STATUS_PRAZO_VENCENDO_HOJE
    if prazo == ref + timedelta(days=1):
        return STATUS_PRAZO_VENCENDO_AMANHA
    if prazo == ref + timedelta(days=2):
        return STATUS_PRAZO_DEPOIS_AMANHA
    return STATUS_PRAZO_FUTURO


def excluir_status_entregue(df: pd.DataFrame) -> pd.DataFrame:
    """Remove linhas com STATUS TMS = ENTREGUE (AutoFilter da consolidada)."""
    if df.empty or "status" not in df.columns:
        return df
    out = df.copy()
    status_norm = out["status"].astype(str).str.strip().str.upper()
    mask = status_norm == STATUS_ENTREGUE
    return out.loc[~mask].reset_index(drop=True)


def aplicar_regras_macros(
    df: pd.DataFrame,
    data_referencia: datetime | date | None = None,
) -> pd.DataFrame:
    """
    Regras calcConsolidada (sem cosmético Excel).

    - Exclui status ENTREGUE
    - STATUS PRAZO só com dt_prazo_atual
    - RETORNO FILIAL sempre vazio
    - atrasado / vence_hoje alinhados ao STATUS PRAZO
    """
    out = excluir_status_entregue(df)
    hoje = pd.Timestamp(data_referencia or datetime.now().date()).normalize()

    out["retorno_filial"] = ""
    out["status_prazo"] = out.get("dt_prazo_atual", pd.Series(dtype=object)).map(
        lambda v: classificar_status_prazo(v, hoje)
    )

    out["prazo_considerado"] = pd.to_datetime(out.get("dt_prazo_atual"), errors="coerce")

    if "dt_cancelamento" in out.columns:
        out["cancelada"] = out["dt_cancelamento"].notna()
    else:
        out["cancelada"] = False
    if "dt_entrega" in out.columns:
        out["entregue"] = out["dt_entrega"].notna()
    else:
        out["entregue"] = False

    out["atrasado"] = out["status_prazo"] == STATUS_PRAZO_ATRASO
    out["vence_hoje"] = out["status_prazo"] == STATUS_PRAZO_VENCENDO_HOJE

    out["dias_atraso"] = np.where(
        out["atrasado"] & out["prazo_considerado"].notna(),
        (hoje - out["prazo_considerado"]).dt.days,
        0,
    )
    return out


# Compat: aliases legados (não usados pelo pipeline consolidado)
CLIENTES_EXCLUIR_MACROS: frozenset[str] = frozenset()
CLIENTES_EXCLUIR_ALIASES: frozenset[str] = frozenset()


def excluir_clientes_macros(df: pd.DataFrame) -> pd.DataFrame:
    """Deprecated: calcConsolidada não exclui por conta. No-op."""
    return df.reset_index(drop=True) if not df.empty else df
