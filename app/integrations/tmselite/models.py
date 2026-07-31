"""Internal models for TMS Elite delivery rows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class DeliveryRecord:
    remessa_numero: str
    nro_entrega: str
    nota_fiscal: Optional[str] = None
    cliente: Optional[str] = None
    cliente_conta: Optional[str] = None
    filial: Optional[str] = None
    cidade_entrega: Optional[str] = None
    uf_entrega: Optional[str] = None
    status: Optional[str] = None
    valor_total: Optional[float] = None
    qtde_volumes: Optional[float] = None
    dt_prazo_atual: Optional[datetime] = None
    dt_agendamento: Optional[datetime] = None
    dt_entrega: Optional[datetime] = None
    dt_recebimento: Optional[datetime] = None
    dt_cancelamento: Optional[datetime] = None
    motivo_cancelamento: Optional[str] = None
    motivo_atraso: Optional[str] = None
    nome_recebedor: Optional[str] = None
    dt_cadastro: Optional[datetime] = None
    motorista: Optional[str] = None
    remetente: Optional[str] = None
    cidade_remetente: Optional[str] = None
    uf_remetente: Optional[str] = None
    peso_taxado: Optional[float] = None
    peso_informado: Optional[float] = None
    raw_json: Optional[dict[str, Any]] = field(default=None, repr=False)


@dataclass
class FetchPageResult:
    items: list[dict[str, Any]]
    current_page: int
    total_pages: Optional[int]
    page_size: int
    total_results: Optional[int]
