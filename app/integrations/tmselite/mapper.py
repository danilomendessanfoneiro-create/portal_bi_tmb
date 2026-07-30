"""Map TMS Elite JSON items to internal DeliveryRecord."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.integrations.tmselite.exceptions import TmsEliteMappingError
from app.integrations.tmselite.models import DeliveryRecord


def _dig(data: dict[str, Any], *path: str) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_dt(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", ""))
    except ValueError:
        return None


def map_delivery_item(item: dict[str, Any]) -> DeliveryRecord:
    remessa_numero = _as_str(_dig(item, "remessa", "numero"))
    if not remessa_numero:
        raise TmsEliteMappingError("Item sem remessa.numero")

    doc_num = _dig(item, "documentos", "numero")
    doc_serie = _dig(item, "documentos", "serie")
    if doc_num is not None and doc_serie is not None:
        nota_fiscal = f"{doc_num}/{doc_serie}"
    else:
        nota_fiscal = _as_str(doc_num)

    peso = _dig(item, "documentos", "peso") or {}
    if not isinstance(peso, dict):
        peso = {}

    filial = (
        _as_str(_dig(item, "unidadeEntrega", "sigla"))
        or _as_str(_dig(item, "unidadeAtual", "sigla"))
        or _as_str(_dig(item, "embarcador", "nomeFilial"))
    )

    return DeliveryRecord(
        remessa_numero=remessa_numero,
        nro_entrega=remessa_numero,
        nota_fiscal=nota_fiscal,
        cliente=_as_str(_dig(item, "destinatario", "nome")),
        filial=filial,
        cidade_entrega=_as_str(_dig(item, "destinatario", "cidade")),
        uf_entrega=_as_str(_dig(item, "destinatario", "uf")),
        status=_as_str(_dig(item, "remessa", "status")),
        valor_total=_as_float(_dig(item, "documentos", "valor")),
        qtde_volumes=_as_float(_dig(item, "documentos", "qtdeVolumes")),
        dt_prazo_atual=_as_dt(_dig(item, "prazo", "atual")),
        dt_agendamento=_as_dt(_dig(item, "agendamento", "atual")),
        dt_entrega=_as_dt(_dig(item, "fluxo", "entrega")),
        dt_cancelamento=_as_dt(_dig(item, "fluxo", "cancelamento")),
        motivo_cancelamento=None,
        motivo_atraso=_as_str(_dig(item, "ocorrencia", "observacao")),
        nome_recebedor=_as_str(_dig(item, "recebedor", "nome")),
        dt_cadastro=_as_dt(_dig(item, "fluxo", "cadastro")),
        motorista=_as_str(_dig(item, "romaneio", "motorista")),
        remetente=_as_str(_dig(item, "remetente", "nome")),
        cidade_remetente=_as_str(_dig(item, "remetente", "cidade")),
        uf_remetente=_as_str(_dig(item, "remetente", "uf")),
        peso_taxado=_as_float(peso.get("taxado")),
        peso_informado=_as_float(peso.get("informado")),
        raw_json=item,
    )
