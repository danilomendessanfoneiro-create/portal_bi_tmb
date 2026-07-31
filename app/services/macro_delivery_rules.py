"""Regras de negócio espelhadas das macros Excel calc1/calc2 (paridade 100%)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Union

import numpy as np
import pandas as pd

# calc1.vb — exclusão por AutoFilter na coluna Excel "Cliente" (não é o destinatário)
CLIENTES_EXCLUIR_MACROS: frozenset[str] = frozenset(
    {
        "NINFA INDUSTRIA DE ALIMENTOS LTDA",
        "MINAS MAIS ALIMENTOS LTDA",
        "PREDILECTA ALIMENTOS LTDA",
        "SO FRUTA ALIMENTOS LTDA",
        "STELLA DORO ALIMENTOS LTDA",
    }
)

# Variações em "Nome Remetente" / API que correspondem às contas excluídas no Excel
CLIENTES_EXCLUIR_ALIASES: frozenset[str] = frozenset(
    {
        "NINFA ALIMENTOS LTDA",
    }
)

STATUS_PRAZO_ATRASO = "01_ATRASO"
STATUS_PRAZO_VENCENDO_HOJE = "02_VENCENDO HOJE"
STATUS_PRAZO_VENCENDO_AMANHA = "03_VENCENDO AMANHÃ"
STATUS_PRAZO_DEPOIS_AMANHA = "04_DEPOIS DE AMANHÃ"
STATUS_PRAZO_FUTURO = "05_VENCIMENTO FUTURO"

DateLike = Union[date, datetime, pd.Timestamp, None]


def _nomes_excluir_normalizados() -> set[str]:
    return {c.upper() for c in CLIENTES_EXCLUIR_MACROS} | {
        c.upper() for c in CLIENTES_EXCLUIR_ALIASES
    }


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
    """
    calc1: Select Case em Dt. Prazo Atual vs Date (sem usar Dt. Agendamento).
    Sem data → string vazia.
    """
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


def excluir_clientes_macros(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove contas da lista calc1.

    Prioridade (paridade Excel):
    1. cliente_conta ← coluna planilha "Cliente"
    2. remetente ← Nome Remetente / API (com aliases, ex. NINFA ALIMENTOS)
    Não usa destinatário (Nome Pessoa Visita → cliente) como chave de exclusão.
    """
    if df.empty:
        return df
    out = df.copy()
    excluir = _nomes_excluir_normalizados()
    mask = pd.Series(False, index=out.index)

    if "cliente_conta" in out.columns:
        mask |= out["cliente_conta"].astype(str).str.strip().str.upper().isin(excluir)

    if "remetente" in out.columns:
        mask |= out["remetente"].astype(str).str.strip().str.upper().isin(excluir)

    return out.loc[~mask].reset_index(drop=True)


def aplicar_regras_macros(
    df: pd.DataFrame,
    data_referencia: datetime | date | None = None,
) -> pd.DataFrame:
    """
    Conversão das regras de negócio das macros (sem cosmético Excel).

    - Exclui contas da lista calc1 (Cliente Excel / remetente)
    - STATUS PRAZO só com dt_prazo_atual
    - RETORNO FILIAL sempre vazio (cliente confirmou: existe mas não usam)
    - atrasado / vence_hoje alinhados ao STATUS PRAZO (paridade Excel)
    """
    out = excluir_clientes_macros(df)
    hoje = pd.Timestamp(data_referencia or datetime.now().date()).normalize()

    out["retorno_filial"] = ""
    out["status_prazo"] = out.get("dt_prazo_atual", pd.Series(dtype=object)).map(
        lambda v: classificar_status_prazo(v, hoje)
    )

    # Paridade Excel: prazo considerado = só Dt. Prazo Atual
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
