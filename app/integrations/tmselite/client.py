"""HTTP client for TMS Elite deliveries report API."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

from app.integrations.tmselite.exceptions import TmsEliteHttpError
from app.integrations.tmselite.models import FetchPageResult

logger = logging.getLogger("tmselite.client")


class TmsEliteClient:
    def __init__(
        self,
        *,
        base_url: str,
        endpoint: str,
        token: str,
        timeout_seconds: int = 60,
        page_size: int = 500,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.endpoint = endpoint.lstrip("/")
        self.token = token.strip()
        if self.token.lower().startswith("bearer "):
            self.token = self.token[7:].strip()
        self.timeout_seconds = timeout_seconds
        self.page_size = page_size

    def _url(self) -> str:
        return urljoin(self.base_url, self.endpoint)

    def fetch_page(
        self,
        *,
        data_inicio: date,
        data_fim: date,
        current_page: int = 1,
        id_status: Optional[str] = None,
        id_servico: Optional[str] = None,
    ) -> FetchPageResult:
        params: dict[str, Any] = {
            "dataCadastroInicio": data_inicio.isoformat(),
            "dataCadastroFim": data_fim.isoformat(),
            "currentPage": current_page,
            "pageSize": self.page_size,
        }
        if id_status:
            params["idStatus"] = id_status
        if id_servico:
            params["idServico"] = id_servico

        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        url = self._url()
        logger.info(
            "GET %s page=%s size=%s range=%s..%s",
            url,
            current_page,
            self.page_size,
            data_inicio,
            data_fim,
        )
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(url, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise TmsEliteHttpError(f"Timeout ao chamar TMS Elite: {exc}") from exc
        except httpx.HTTPError as exc:
            raise TmsEliteHttpError(f"Erro de rede TMS Elite: {exc}") from exc

        if response.status_code >= 400:
            raise TmsEliteHttpError(
                f"HTTP {response.status_code}: {response.text[:300]}",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise TmsEliteHttpError("Resposta JSON inválida da TMS Elite") from exc

        root = payload.get("result", payload) if isinstance(payload, dict) else {}
        if not isinstance(root, dict):
            raise TmsEliteHttpError("Envelope de resposta inesperado da TMS Elite")

        results = root.get("results") or []
        if not isinstance(results, list):
            raise TmsEliteHttpError("Campo results inválido na resposta TMS Elite")

        pager = root.get("pager") or {}
        if not isinstance(pager, dict):
            pager = {}

        return FetchPageResult(
            items=results,
            current_page=int(pager.get("currentPage") or current_page),
            total_pages=int(pager["totalPages"]) if pager.get("totalPages") is not None else None,
            page_size=int(pager.get("pageSize") or self.page_size),
            total_results=int(pager["totalResults"]) if pager.get("totalResults") is not None else None,
        )

    def iter_all_pages(
        self,
        *,
        data_inicio: date,
        data_fim: date,
        id_status: Optional[str] = None,
        id_servico: Optional[str] = None,
        max_pages: int = 10_000,
    ):
        page = 1
        while page <= max_pages:
            result = self.fetch_page(
                data_inicio=data_inicio,
                data_fim=data_fim,
                current_page=page,
                id_status=id_status,
                id_servico=id_servico,
            )
            yield result
            if not result.items:
                break
            if result.total_pages is not None:
                if page >= result.total_pages:
                    break
            elif len(result.items) < result.page_size:
                break
            page += 1
