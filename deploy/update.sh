#!/usr/bin/env bash
# Deploy rotineiro do Portal BI TMB na VPS.
# Uso (em /opt/portal-bi-tmb, com sudo se ownership exigir):
#   ./deploy/update.sh
#   ./deploy/update.sh --branch master --with-units
#   ./deploy/update.sh --skip-pull --skip-frontend
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BRANCH="master"
DO_PULL=1
DO_PIP=1
DO_MIGRATE=1
DO_FRONTEND=1
DO_RESTART=1
DO_UNITS=0
DO_SEED_CLIENTS=0
SEED_CLIENTS_CSV=""
HEALTH_URL="http://127.0.0.1:8000/api/health"

usage() {
  cat <<'EOF'
Uso: ./deploy/update.sh [opções]

  --branch NAME              Branch para pull (default: master)
  --skip-pull                Não executa git pull
  --skip-pip                 Não atualiza requirements
  --skip-migrate             Não roda migrations
  --skip-frontend            Não faz npm ci/build
  --skip-restart             Não reinicia systemd
  --with-units               Copia units systemd + nginx e recarrega
  --seed-clients             Roda seed de prb_clients a partir do CSV
  --seed-clients-csv PATH    CSV para o seed (default: dados/entregas_relatorio.csv)
  --health-url URL           Smoke check (default: http://127.0.0.1:8000/api/health)
  -h, --help                 Ajuda
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch) BRANCH="${2:-}"; shift 2 ;;
    --skip-pull) DO_PULL=0; shift ;;
    --skip-pip) DO_PIP=0; shift ;;
    --skip-migrate) DO_MIGRATE=0; shift ;;
    --skip-frontend) DO_FRONTEND=0; shift ;;
    --skip-restart) DO_RESTART=0; shift ;;
    --with-units) DO_UNITS=1; shift ;;
    --seed-clients) DO_SEED_CLIENTS=1; shift ;;
    --seed-clients-csv) SEED_CLIENTS_CSV="${2:-}"; DO_SEED_CLIENTS=1; shift 2 ;;
    --health-url) HEALTH_URL="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opção desconhecida: $1" >&2; usage; exit 1 ;;
  esac
done

log() { printf '\n==> %s\n' "$*"; }

if [[ ! -d .venv ]]; then
  echo "Erro: .venv não encontrado em $ROOT" >&2
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate

if [[ "$DO_RESTART" -eq 1 ]]; then
  log "Parando serviços (se existirem)"
  sudo systemctl stop portal-bi portal-api 2>/dev/null || true
fi

if [[ "$DO_PULL" -eq 1 ]]; then
  log "git fetch + checkout/pull $BRANCH"
  git fetch origin
  git checkout "$BRANCH"
  git pull --ff-only origin "$BRANCH"
fi

if [[ "$DO_PIP" -eq 1 ]]; then
  log "pip install -r requirements.txt"
  pip install -r requirements.txt
  log "Playwright Chromium (coleta TMS)"
  python -m playwright install chromium
fi

if [[ "$DO_MIGRATE" -eq 1 ]]; then
  log "Migrations"
  python database/deploy/run_migrations.py
fi

if [[ "$DO_SEED_CLIENTS" -eq 1 ]]; then
  CSV_PATH="${SEED_CLIENTS_CSV:-dados/entregas_relatorio.csv}"
  log "Seed clientes ($CSV_PATH)"
  if [[ ! -f "$CSV_PATH" ]]; then
    echo "Erro: CSV não encontrado: $CSV_PATH" >&2
    echo "Envie a planilha para o servidor ou use --seed-clients-csv /caminho/arquivo.csv" >&2
    exit 1
  fi
  python database/deploy/seed_clients_from_csv.py --csv "$CSV_PATH"
fi

if [[ "$DO_FRONTEND" -eq 1 ]]; then
  log "Build Admin (npm ci + build)"
  (
    cd frontend
    npm ci
    npm run build
  )
fi

if [[ "$DO_UNITS" -eq 1 ]]; then
  log "Atualizando units systemd e nginx"
  sudo cp deploy/systemd/*.service /etc/systemd/system/
  sudo cp deploy/systemd/*.timer /etc/systemd/system/ 2>/dev/null || true
  if [[ -f deploy/nginx/portal-bi-tmb.conf ]]; then
    sudo cp deploy/nginx/portal-bi-tmb.conf /etc/nginx/sites-available/portal-bi-tmb
  fi
  sudo systemctl daemon-reload
  if command -v nginx >/dev/null 2>&1; then
    sudo nginx -t && sudo systemctl reload nginx
  fi
fi

if [[ "$DO_RESTART" -eq 1 ]]; then
  log "Reiniciando portal-api e portal-bi"
  sudo systemctl start portal-api portal-bi
  sudo systemctl restart portal-api portal-bi
  sudo systemctl status portal-api portal-bi --no-pager || true
fi

log "Health check: $HEALTH_URL"
if command -v curl >/dev/null 2>&1; then
  curl -sfS "$HEALTH_URL" || echo "(health falhou — confira logs: journalctl -u portal-api -n 80)"
else
  echo "curl ausente; pule o smoke check."
fi

log "Deploy concluído."
echo "Pós-deploy:"
echo "  - smoke /admin /api/health /bi"
echo "  - confirmar migrations 040–042 e TECH_SMTP_* no .env"
echo "  - Automações: 4 cards + dias; coleta TMS + timers"
echo "  - ver docs/release-automacoes-monitoramento.md"
if [[ "$DO_SEED_CLIENTS" -eq 0 ]]; then
  echo "Clientes: rode com --seed-clients se prb_clients estiver vazio."
fi
