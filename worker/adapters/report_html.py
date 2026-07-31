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


def build_report_subject(audience_name: str) -> str:
    return f"Relatório de Entregas - {audience_name}"


def build_report_html(
    *,
    audience_name: str,
    overdue: pd.DataFrame,
    due_today: Optional[pd.DataFrame] = None,
) -> str:
    overdue = overdue if overdue is not None else pd.DataFrame()
    due_today = due_today if due_today is not None else pd.DataFrame()
    n_overdue = len(overdue)
    n_due = len(due_today)
    overdue_block = _table_html(overdue) if n_overdue else f"<p>{EMPTY_MSG}</p>"
    due_block = _table_html(due_today) if n_due else f"<p>{EMPTY_MSG}</p>"
    return f"""\
<html><body style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#222;line-height:1.45;">
<p><strong>Olá, bom dia!</strong></p>
<p><strong>{audience_name},</strong></p>
<p>Segue relatório de notas em atraso da sua filial.<br>
Peço que baixe os canhotos com urgência e para as notas que serão entregues em atraso
favor retornar com a previsão.</p>
<p><strong>Notas fiscais em atraso ({n_overdue})</strong></p>
{overdue_block}
<p><strong>Notas fiscais que vencem hoje ({n_due})</strong></p>
{due_block}
<p>Atenciosamente.</p>
</body></html>
"""
