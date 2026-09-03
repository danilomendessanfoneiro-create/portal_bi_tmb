"""Filtro de Cliente no BI = cliente indústria (`cliente_conta`), não destinatário."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

EMPTY = {"", "nan", "none", "nat", "<na>"}


def unique_cliente_industria(df: pd.DataFrame) -> list[str]:
    if df is None or df.empty:
        return []
    col = "cliente_conta" if "cliente_conta" in df.columns else "cliente"
    if col not in df.columns:
        return []
    series = df[col].dropna().astype(str).str.strip()
    return sorted({v for v in series if v and v.lower() not in EMPTY})


def apply_cliente_industria_filter(df: pd.DataFrame, selected: Iterable | None) -> pd.DataFrame:
    if df is None or df.empty or not selected:
        return df
    names = [str(x).strip() for x in selected if str(x).strip()]
    if not names:
        return df
    col = "cliente_conta" if "cliente_conta" in df.columns else "cliente"
    if col not in df.columns:
        return df
    return df[df[col].astype(str).str.strip().isin(names)]


def industria_dim_col(df: pd.DataFrame) -> str:
    if df is not None and not df.empty and "cliente_conta" in df.columns:
        series = df["cliente_conta"].dropna().astype(str).str.strip()
        if any(v and v.lower() not in EMPTY for v in series):
            return "cliente_conta"
    return "cliente"
