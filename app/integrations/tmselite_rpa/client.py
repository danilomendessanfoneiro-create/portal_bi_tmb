"""Playwright: login TMS → Total → Ver Entregas → Excel → download.

Isolado da regra de negócio do Portal BI. Retorna só o arquivo.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import settings
from app.integrations.tmselite_rpa.exceptions import TmsRpaError

logger = logging.getLogger("worker")

REPORT_PATH = "/EntregasRelatorios/RelatorioGeralEntregas"
LOGIN_WAIT_MS = 45_000
NAV_WAIT_MS = 30_000
POPOVER_WAIT_MS = 90_000
EXPORT_WAIT_MS = 180_000
DOWNLOAD_WAIT_MS = 90_000


@dataclass(frozen=True)
class SpreadsheetDownload:
    file_name: str
    content: bytes
    sha256: str
    size_bytes: int
    saved_path: Path


def _require_playwright():
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise TmsRpaError(
            "Playwright não instalado. pip install playwright && playwright install chromium",
            step="setup",
        ) from exc
    return sync_playwright, PlaywrightTimeout


def _trace_dir() -> Path:
    path = settings.root_dir / "storage" / "rpa" / "traces"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _download_dir() -> Path:
    path = settings.root_dir / "storage" / "rpa" / "downloads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _dump(page, step: str) -> None:
    folder = _trace_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    png = folder / f"{stamp}_{step}.png"
    html = folder / f"{stamp}_{step}.html"
    try:
        page.screenshot(path=str(png), full_page=True)
        html.write_text(page.content(), encoding="utf-8")
        logger.info("dump step=%s png=%s", step, png)
    except Exception:
        logger.exception("falha no dump step=%s", step)


def _screenshot(page, step: str) -> Optional[Path]:
    _dump(page, step)
    return None


def _click_ver_entregas(page):
    pop = page.locator(".popover").filter(has_text=re.compile(r"Detalhamento das Entregas", re.I)).first
    try:
        pop.locator(".carregando").wait_for(state="hidden", timeout=POPOVER_WAIT_MS)
    except Exception:
        logger.info("Spinner do popover ainda visível; tentando o botão")
    btn = pop.locator("input[type='submit'][name='enviar'], input[type='submit'][value*='Ver Entregas']").first
    btn.wait_for(state="visible", timeout=POPOVER_WAIT_MS)
    _dump(page, "after_total")
    logger.info("Clique em Ver Entregas (nova aba)")
    with page.expect_popup(timeout=NAV_WAIT_MS) as popup_info:
        btn.click()
    report = popup_info.value
    report.set_default_timeout(NAV_WAIT_MS)
    report.wait_for_load_state("domcontentloaded", timeout=NAV_WAIT_MS)
    return report


def _click_first(page, locators: list, *, timeout: int, step: str):
    last_err: Optional[Exception] = None
    for locator in locators:
        try:
            target = locator.first
            target.wait_for(state="visible", timeout=timeout)
            target.click(timeout=timeout)
            return
        except Exception as exc:
            last_err = exc
    raise TmsRpaError(f"Elemento não encontrado ({step}): {last_err}", step=step) from last_err


def download_geral_entregas(
    *,
    login_url: str,
    username: str,
    password: str,
    headless: bool = True,
    timeout_ms: int = EXPORT_WAIT_MS,
) -> SpreadsheetDownload:
    if not login_url or not username or not password:
        raise TmsRpaError("URL, usuário e senha do TMS são obrigatórios.", step="config")

    sync_playwright, PlaywrightTimeout = _require_playwright()
    dest_dir = _download_dir()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        page.set_default_timeout(NAV_WAIT_MS)
        current = page
        try:
            _login(page, login_url, username, password)
            current = _open_report_from_total(page)
            _select_excel_and_search(current)
            downloaded = _wait_and_download(current, dest_dir, timeout_ms=timeout_ms)
        except TmsRpaError:
            _screenshot(current, "error")
            raise
        except PlaywrightTimeout as exc:
            _screenshot(current, "timeout")
            raise TmsRpaError(f"Timeout no TMS Elite: {exc}", step="timeout") from exc
        except Exception as exc:
            _screenshot(current, "error")
            raise TmsRpaError(str(exc), step="unexpected") from exc
        finally:
            context.close()
            browser.close()

    return downloaded


def _login(page, login_url: str, username: str, password: str) -> None:
    logger.info("Abrindo login TMS: %s", login_url)
    page.goto(login_url, wait_until="domcontentloaded")
    user_field = page.locator(
        "input[name='Email'], input[name='login'], input[name='Login'], "
        "input[type='text']:visible, input[type='email']:visible"
    ).first
    pass_field = page.locator("input[name='Password'], input[name='senha'], input[type='password']:visible").first
    try:
        user_field.wait_for(state="visible", timeout=LOGIN_WAIT_MS)
    except Exception as exc:
        raise TmsRpaError("Campo de login não encontrado.", step="login") from exc
    user_field.fill(username)
    pass_field.fill(password)
    _click_first(
        page,
        [
            page.get_by_role("button", name=re.compile(r"ENTRAR|Entrar", re.I)),
            page.locator("button[type='submit']"),
            page.locator("input[type='submit']"),
        ],
        timeout=LOGIN_WAIT_MS,
        step="login",
    )
    try:
        page.wait_for_url(re.compile(r".*/home/index.*"), timeout=LOGIN_WAIT_MS)
    except Exception:
        if "/login" in (page.url or ""):
            raise TmsRpaError("Login recusado ou credenciais inválidas.", step="login")
        page.wait_for_load_state("networkidle", timeout=LOGIN_WAIT_MS)
    if "/login" in (page.url or ""):
        raise TmsRpaError("Permaneceu na tela de login.", step="login")
    logger.info("Login TMS concluído url=%s", page.url)
    try:
        page.get_by_text("Cenário Entregas").first.wait_for(timeout=LOGIN_WAIT_MS)
    except Exception:
        logger.info("Título Cenário Entregas ainda não visível")
    page.wait_for_timeout(2500)


def _open_report_from_total(page):
    logger.info("Abrindo detalhe Total → Ver Entregas")
    _dump(page, "after_login")
    page.locator("#totalEntregas").wait_for(state="attached", timeout=NAV_WAIT_MS)
    total_link = page.locator(
        "a[data-url='/WidGets/WidgetCenarioEntregas/widget-cenario-entregas-detalhes']"
    )
    total_link.first.scroll_into_view_if_needed()
    total_link.first.click(force=True, timeout=NAV_WAIT_MS)
    logger.info("Clique no Total do Cenário Entregas")
    try:
        page.locator(".popover").filter(has_text=re.compile(r"Detalhamento das Entregas", re.I)).first.wait_for(
            timeout=NAV_WAIT_MS
        )
    except Exception:
        page.get_by_text("Detalhamento das Entregas").first.wait_for(timeout=NAV_WAIT_MS)
    try:
        report = _click_ver_entregas(page)
    except Exception as exc:
        _dump(page, "after_total")
        raise TmsRpaError("Botão Ver Entregas não apareceu após o Total.", step="navigate") from exc
    _wait_report_page(report)
    return report


def _wait_report_page(page) -> None:
    try:
        page.wait_for_url(re.compile(r".*RelatorioGeralEntrega.*"), timeout=NAV_WAIT_MS)
    except Exception:
        page.get_by_text("Relatório Geral de Entregas").first.wait_for(timeout=NAV_WAIT_MS)
    logger.info("Relatório Geral aberto url=%s", page.url)


def _select_excel_and_search(page) -> None:
    logger.info("Selecionando Excel e disparando busca")
    excel_ok = False
    select = page.locator("#tipoSaida")
    if select.count():
        try:
            select.first.select_option(label="Excel")
            excel_ok = True
        except Exception:
            try:
                select.first.select_option(value="Excel")
                excel_ok = True
            except Exception:
                excel_ok = False
    if not excel_ok:
        _click_first(
            page,
            [
                page.get_by_label(re.compile(r"EXIBIR", re.I)),
                page.locator("select").filter(has_text="Excel"),
            ],
            timeout=NAV_WAIT_MS,
            step="export",
        )
        try:
            page.locator("select").filter(has_text="Excel").first.select_option(label="Excel")
        except Exception:
            page.get_by_text("Excel", exact=True).first.click()

    _click_first(
        page,
        [
            page.locator("input[value='Buscar']"),
            page.get_by_role("button", name=re.compile(r"^Buscar$", re.I)),
            page.locator("button:has-text('Buscar')"),
        ],
        timeout=NAV_WAIT_MS,
        step="export",
    )
    logger.info("Busca disparada, aguardando processamento")


def _wait_and_download(page, dest_dir: Path, *, timeout_ms: int) -> SpreadsheetDownload:
    download_btn = page.locator("#btDownload, button:has-text('Download'), a:has-text('Download')").last
    try:
        page.get_by_text("100%", exact=True).wait_for(timeout=timeout_ms)
    except Exception:
        logger.info("Marcador 100% não visível; aguardando botão Download")
    try:
        download_btn.wait_for(state="visible", timeout=timeout_ms)
    except Exception as exc:
        raise TmsRpaError("Download não ficou disponível após o processamento.", step="download") from exc

    with page.expect_download(timeout=DOWNLOAD_WAIT_MS) as info:
        download_btn.click()
    download = info.value
    name = download.suggested_filename or f"entregas_relatorio_{datetime.now():%Y%m%d_%H%M%S}.csv"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    saved = dest_dir / safe
    download.save_as(str(saved))
    if not saved.is_file() or saved.stat().st_size <= 0:
        raise TmsRpaError("Arquivo baixado vazio ou incompleto.", step="download")
    content = saved.read_bytes()
    logger.info("Arquivo baixado: %s (%s bytes)", saved.name, len(content))
    return SpreadsheetDownload(
        file_name=name,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        saved_path=saved,
    )
