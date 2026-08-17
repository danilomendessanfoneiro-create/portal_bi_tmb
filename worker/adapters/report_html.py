"""Build HTML e-mail body for overdue / due-today delivery reports."""

from __future__ import annotations

from typing import Optional

import pandas as pd

HTML_COLUMNS = [
    ("nota_fiscal", "Nota Fiscal"),
    ("cliente", "Cliente"),
    ("cidade_entrega", "Cidade"),
    ("dt_agendamento", "Dt. Agendamento"),
    ("motorista", "Ult. Motorista"),
    ("dias_atraso", "Dias em atraso"),
]

EMPTY_MSG = "Nenhuma nota fiscal nesta situação."
DUE_TODAY_HINT = "Dias em atraso igual a 0 indica nota que vence hoje."


def _fmt_date(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, str) and not value.strip():
        return ""
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return ""
    return ts.strftime("%d/%m/%Y")


def _fmt_text(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if text.lower() in {"nan", "nat", "none", "<na>"}:
        return ""
    return text


def _table_html(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return f"<p>{EMPTY_MSG}</p>"
    rows = []
    for _, row in df.iterrows():
        cells = []
        for src, _label in HTML_COLUMNS:
            val = row[src] if src in row.index else ""
            if src == "dt_agendamento":
                cells.append(
                    f'<td style="border:1px solid #ccc;padding:6px;text-align:center;">{_fmt_date(val)}</td>'
                )
            elif src == "dias_atraso":
                try:
                    if pd.isna(val):
                        dias = ""
                    else:
                        dias = int(val)
                except (TypeError, ValueError):
                    dias = _fmt_text(val)
                cells.append(
                    f'<td style="border:1px solid #ccc;padding:6px;text-align:center;">{dias}</td>'
                )
            else:
                cells.append(
                    f'<td style="border:1px solid #ccc;padding:6px;">{_fmt_text(val)}</td>'
                )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    headers = "".join(
        f'<th style="border:1px solid #ccc;padding:6px;background:#f2f2f2;text-align:left;">{label}</th>'
        for _src, label in HTML_COLUMNS
    )
    return (
        '<table cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%;'
        'max-width:720px;font-family:Arial,Helvetica,sans-serif;font-size:13px;">'
        f"<thead><tr>{headers}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def combine_report_rows(
    overdue: Optional[pd.DataFrame],
    due_today: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Uma tabela: atrasados + vence hoje (dias_atraso = 0)."""
    frames: list[pd.DataFrame] = []
    if overdue is not None and not overdue.empty:
        frames.append(overdue.copy())
    if due_today is not None and not due_today.empty:
        due = due_today.copy()
        due["dias_atraso"] = 0
        frames.append(due)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    if "nro_entrega" in combined.columns:
        combined = combined.drop_duplicates(subset=["nro_entrega"], keep="first")
    elif "nota_fiscal" in combined.columns:
        combined = combined.drop_duplicates(subset=["nota_fiscal"], keep="first")
    if "dias_atraso" in combined.columns:
        combined["dias_atraso"] = (
            pd.to_numeric(combined["dias_atraso"], errors="coerce").fillna(0).astype(int)
        )
        combined = combined.sort_values("dias_atraso", ascending=False, kind="mergesort")
    return combined.reset_index(drop=True)


def build_report_subject(audience_name: str) -> str:
    return f"Relatório de Entregas - {audience_name}"


def build_report_html(
    *,
    audience_name: str,
    overdue: pd.DataFrame,
    due_today: Optional[pd.DataFrame] = None,
) -> str:
    combined = combine_report_rows(overdue, due_today)
    n_notes = len(combined)
    table_block = _table_html(combined) if n_notes else f"<p>{EMPTY_MSG}</p>"
    hint = f"<p>{DUE_TODAY_HINT}</p>" if n_notes else ""
    return f"""\
<html><body style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#222;line-height:1.45;">
<p><strong>Olá, bom dia!</strong></p>
<p><strong>{audience_name},</strong></p>
<p>Segue relatório de notas em atraso da sua filial.<br>
Peço que baixe os canhotos com urgência e para as notas que serão entregues em atraso
favor retornar com a previsão.</p>
<p><strong>Notas Fiscais em atraso ({n_notes})</strong></p>
{hint}{table_block}
<p>Atenciosamente.</p>
</body></html>
"""
