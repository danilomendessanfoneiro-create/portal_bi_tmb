"""
tmb_automation.py
==================
Substitui o robo do Power Automate Desktop que:
  1) Faz login no portal TMB (tmblogistica.tmselite.com), gera e baixa o
     "Relatorio Geral de Entregas" em Excel/CSV.
  2) Faz login no painel admin (179.198.101.65/admin), envia o arquivo
     baixado na tela de "Importacao de Dados" e clica em
     "Validar planilha" -> "Importar dados".

Requisitos:
    pip install -r requirements.txt
    (precisa do Google Chrome instalado; o chromedriver e baixado
     automaticamente pelo webdriver-manager)

Configuracao:
    Copie ".env.example" para ".env" e preencha usuario/senha e demais
    parametros antes de rodar.

ATENCAO - AJUSTES NECESSARIOS ANTES DE USAR EM PRODUCAO:
    O fluxo original gravado no Power Automate NAO capturava a digitacao
    de usuario/senha em nenhum dos dois logins (provavelmente por
    autofill do navegador). Os seletores de campos de login abaixo
    (USER_FIELD_SELECTOR, PASS_FIELD_SELECTOR, ADMIN_USER_SELECTOR,
    ADMIN_PASS_SELECTOR) sao PLACEHOLDERS. Abra o site, clique com o
    botao direito no campo de usuario/senha -> "Inspecionar" e ajuste os
    seletores CSS/By abaixo para os valores reais antes de agendar a
    execucao automatica.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# --------------------------------------------------------------------------- #
# Configuracao
# --------------------------------------------------------------------------- #

load_dotenv()

TMB_URL = os.getenv("TMB_LOGIN_URL", "https://tmblogistica.tmselite.com/login?ReturnUrl=%2F")
TMB_USER = os.getenv("TMB_USER", "")
TMB_PASS = os.getenv("TMB_PASS", "")

ADMIN_URL = os.getenv("ADMIN_LOGIN_URL", "http://179.198.101.65/admin/login")
ADMIN_USER = os.getenv("ADMIN_USER", "")
ADMIN_PASS = os.getenv("ADMIN_PASS", "")

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", str(Path.home() / "Downloads" / "tmb_automation")))
LOG_DIR = Path(os.getenv("LOG_DIR", str(Path(__file__).parent / "logs")))

WAIT_TIMEOUT = int(os.getenv("WAIT_TIMEOUT", "30"))
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

# --- Seletores que provavelmente precisam de ajuste (ver aviso acima) --- #
USER_FIELD_SELECTOR = (By.NAME, "Email")          # PLACEHOLDER - ajustar
PASS_FIELD_SELECTOR = (By.NAME, "Password")        # PLACEHOLDER - ajustar
LOGIN_BUTTON_SELECTOR = (By.XPATH, "//button[contains(., 'ENTRAR')]")

ADMIN_USER_SELECTOR = (By.NAME, "username")        # PLACEHOLDER - ajustar
ADMIN_PASS_SELECTOR = (By.NAME, "password")         # PLACEHOLDER - ajustar
ADMIN_LOGIN_BUTTON_SELECTOR = (By.XPATH, "//button[@type='submit']")

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"tmb_automation_{datetime.now():%Y-%m-%d}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("tmb_automation")


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

def build_driver() -> webdriver.Chrome:
    """Cria uma instancia do Chrome configurada para baixar arquivos
    automaticamente (sem dialogo) em DOWNLOAD_DIR."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    prefs = {
        "download.default_directory": str(DOWNLOAD_DIR),
        "download.prompt_for_download": False,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(5)
    return driver


def wait_for(driver, selector, timeout=WAIT_TIMEOUT):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located(selector))


def wait_clickable(driver, selector, timeout=WAIT_TIMEOUT):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(selector))


# --------------------------------------------------------------------------- #
# Etapa 1: portal TMB - login + download do relatorio
# --------------------------------------------------------------------------- #

def login_tmb(driver) -> None:
    log.info("Abrindo login do portal TMB: %s", TMB_URL)
    driver.get(TMB_URL)

    if not TMB_USER or not TMB_PASS:
        raise RuntimeError(
            "TMB_USER/TMB_PASS nao configurados. Preencha o arquivo .env."
        )

    user_field = wait_for(driver, USER_FIELD_SELECTOR)
    user_field.clear()
    user_field.send_keys(TMB_USER)

    pass_field = wait_for(driver, PASS_FIELD_SELECTOR)
    pass_field.clear()
    pass_field.send_keys(TMB_PASS)

    wait_clickable(driver, LOGIN_BUTTON_SELECTOR).click()

    # Confirma que saiu da tela de login
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.url_contains("home/index")
    )
    log.info("Login no portal TMB concluido.")


def download_report(driver) -> Path:
    """Navega ate o Relatorio Geral de Entregas, gera em Excel e baixa."""
    report_url = "https://tmblogistica.tmselite.com/EntregasRelatorios/RelatorioGeralEntregas"
    log.info("Abrindo relatorio: %s", report_url)
    driver.get(report_url)

    # Seleciona "Excel" no combo de tipo de saida
    select_el = wait_for(driver, (By.ID, "tipoSaida"))
    Select(select_el).select_by_visible_text("Excel")
    log.info("Tipo de saida definido como Excel.")

    # NOTE: se o relatorio exigir filtros de data obrigatorios, adicione
    # aqui o preenchimento dos campos antes de clicar em "Buscar".

    buscar_btn = wait_clickable(driver, (By.XPATH, "//input[@value='Buscar']"))
    buscar_btn.click()
    log.info("Busca disparada, aguardando resultado...")

    # Espera o link de download ficar disponivel
    download_link = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable((By.ID, "btDownload"))
    )

    files_before = _snapshot_dir(DOWNLOAD_DIR)
    download_link.click()
    log.info("Download iniciado, aguardando conclusao...")

    downloaded_file = _wait_for_new_download(DOWNLOAD_DIR, files_before)
    log.info("Arquivo baixado: %s", downloaded_file)
    return downloaded_file


def _snapshot_dir(directory: Path) -> set[str]:
    return {p.name for p in directory.glob("*")}


def _wait_for_new_download(
    directory: Path, files_before: set[str], timeout: int = 60
) -> Path:
    """Espera aparecer um arquivo novo (que nao seja .crdownload) na
    pasta de download e retorna o caminho completo."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = _snapshot_dir(directory)
        new_files = current - files_before
        finished = [
            f for f in new_files if not f.endswith(".crdownload")
        ]
        if finished:
            # pega o mais recente, caso mais de um apareca
            newest = max(
                (directory / f for f in finished), key=lambda p: p.stat().st_mtime
            )
            return newest
        time.sleep(1)
    raise TimeoutError("Download nao concluido dentro do tempo limite.")


# --------------------------------------------------------------------------- #
# Etapa 2: painel admin - login + upload/importacao
# --------------------------------------------------------------------------- #

def login_admin(driver) -> None:
    log.info("Abrindo login do painel admin: %s", ADMIN_URL)
    driver.get(ADMIN_URL)

    if not ADMIN_USER or not ADMIN_PASS:
        raise RuntimeError(
            "ADMIN_USER/ADMIN_PASS nao configurados. Preencha o arquivo .env."
        )

    try:
        user_field = wait_for(driver, ADMIN_USER_SELECTOR, timeout=10)
    except TimeoutException:
        # Sessao ja pode estar ativa / painel pode nao pedir login de novo
        log.info("Campo de login do admin nao encontrado - assumindo sessao ja autenticada.")
        return

    user_field.clear()
    user_field.send_keys(ADMIN_USER)

    pass_field = wait_for(driver, ADMIN_PASS_SELECTOR)
    pass_field.clear()
    pass_field.send_keys(ADMIN_PASS)

    wait_clickable(driver, ADMIN_LOGIN_BUTTON_SELECTOR).click()
    log.info("Login no painel admin concluido.")


def upload_report(driver, file_path: Path) -> None:
    admin_home = "http://179.198.101.65/admin"
    log.info("Abrindo painel admin: %s", admin_home)
    driver.get(admin_home)

    importacao_link = wait_clickable(
        driver, (By.XPATH, "//a[contains(., 'Importação de Dados')]")
    )
    importacao_link.click()
    log.info("Tela de Importacao de Dados aberta.")

    # Em vez de simular o dialogo nativo do Windows (Selecionar arquivo ->
    # digitar nome -> Abrir), enviamos o caminho direto pro <input type=file>.
    file_input = wait_for(driver, (By.CSS_SELECTOR, "input[type='file']"))
    file_input.send_keys(str(file_path.resolve()))
    log.info("Arquivo selecionado para upload: %s", file_path)

    validar_btn = wait_clickable(
        driver, (By.XPATH, "//button[contains(., 'Validar planilha')]")
    )
    validar_btn.click()
    log.info("Planilha validada.")

    importar_btn = wait_clickable(
        driver, (By.XPATH, "//button[contains(., 'Importar dados')]")
    )
    importar_btn.click()
    log.info("Importacao de dados disparada.")


# --------------------------------------------------------------------------- #
# Orquestracao
# --------------------------------------------------------------------------- #

def run() -> int:
    log.info("=== Iniciando execucao do robo TMB ===")
    driver = None
    try:
        driver = build_driver()

        # Etapa 1: baixar relatorio do portal TMB
        login_tmb(driver)
        report_file = download_report(driver)

        # Etapa 2: subir relatorio no painel admin
        login_admin(driver)
        upload_report(driver, report_file)

        log.info("=== Execucao concluida com sucesso ===")
        return 0

    except Exception:
        log.exception("Falha na execucao do robo.")
        return 1

    finally:
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    sys.exit(run())
