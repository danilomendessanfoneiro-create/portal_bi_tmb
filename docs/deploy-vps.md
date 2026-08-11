# Deploy VPS — Portal BI TMB (runbook completo)

Guia passo a passo para **primeira publicação** e **atualizações** na VPS (Hostinger / Ubuntu).

### Decisões atuais (2026-07-29)

| Tema | Decisão |
|------|---------|
| Acesso inicial | **IP da VPS em HTTP** até o cliente liberar o domínio |
| Branch de publicação | **`master`** |
| Jobs no go-live | Relatório diário **e** import API (initial one-shot + daily no timer) |
| HTTPS | **Depois** do DNS do domínio (Certbot na fase 2) |

Documentos relacionados:

- Plano de ação: `.atlas/plans/2026-07-29-publicacao-vps.md`
- Topologia: [`topologia-hibrida.md`](topologia-hibrida.md)
- Jobs / automações: [`servico-jobs.md`](servico-jobs.md)
- Integração API: [`integracao-api-tmselite.md`](integracao-api-tmselite.md)

---

## Visão do que sobe

| Componente | Como roda | Path público |
|---|---|---|
| Admin (React) | nginx static (`frontend/dist`) | `/admin/` |
| API (FastAPI) | systemd `portal-api` → `:8000` | `/api/` |
| BI (Streamlit) | systemd `portal-bi` → `:8501` | `/bi/` |
| Jobs (worker) | systemd timer `portal-job-report` | CLI |
| Postgres | serviço do SO | interno |

Diretório padrão da aplicação: **`/opt/portal-bi-tmb`**.

```text
Internet
   │
   ▼
nginx (:80/:443)
   ├── /admin/  → frontend/dist
   ├── /api/    → 127.0.0.1:8000
   └── /bi/     → 127.0.0.1:8501
          │
          ▼
     PostgreSQL (portal_bi_tmb)
```

---

## 0. Pré-requisitos (antes do SSH)

- [ ] VPS Ubuntu acessível por SSH (usuário com `sudo`)
- [ ] IP público da VPS conhecido (domínio **ainda não** — fase posterior)
- [ ] Branch **`master`** criada e publicada no remoto (branch de publicação)
- [ ] PostgreSQL instalado (ou a instalar no passo 1)
- [ ] Credenciais: senha forte do Postgres, JWT secret, token TMS Elite, SMTP

---

## 1. Provisionar o sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  git curl build-essential \
  python3 python3-venv python3-pip \
  nginx certbot python3-certbot-nginx \
  postgresql postgresql-contrib
```

### Node.js 20+ (build do Admin)

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v   # v20+
npm -v
```

### PostgreSQL — banco e usuário

```bash
sudo -u postgres psql <<'SQL'
CREATE USER portal_bi WITH PASSWORD 'SENHA_FORTE_AQUI';
CREATE DATABASE portal_bi_tmb OWNER portal_bi;
GRANT ALL PRIVILEGES ON DATABASE portal_bi_tmb TO portal_bi;
\c portal_bi_tmb
GRANT ALL ON SCHEMA public TO portal_bi;
ALTER SCHEMA public OWNER TO portal_bi;
SQL
```

> Na VPS a porta típica é **5432** (não use `5433` do Docker local).

### Diretório da aplicação

```bash
sudo mkdir -p /opt/portal-bi-tmb
sudo chown "$USER":"$USER" /opt/portal-bi-tmb
```

---

## 2. Código

### Primeira vez (clone)

```bash
cd /opt
git clone <URL_DO_REPO> portal-bi-tmb
cd /opt/portal-bi-tmb
git checkout master
```

### Atualização

```bash
cd /opt/portal-bi-tmb
git fetch --all
git checkout master
git pull origin master
```

---

## 3. Python (venv + dependências)

```bash
cd /opt/portal-bi-tmb
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Variáveis de ambiente (`.env`)

```bash
cd /opt/portal-bi-tmb
cp .env.example .env
nano .env   # ou vim
```

Preencha **produção** (exemplo):

```env
DATABASE_URL=postgresql://portal_bi:SENHA_FORTE_AQUI@127.0.0.1:5432/portal_bi_tmb

JWT_SECRET=<gere-com-openssl-rand-hex-32>
JWT_EXPIRE_MINUTES=480
PASSWORD_SALT=tmb-logistica-bi

# Fase 1 (agora) — acesso pelo IP, sem domínio ainda:
PUBLIC_ORIGIN=http://IP_DA_VPS
API_PUBLIC_URL=http://IP_DA_VPS/api
ADMIN_PUBLIC_URL=http://IP_DA_VPS/admin
BI_PUBLIC_URL=http://IP_DA_VPS/bi

# Fase 2 (quando o cliente liberar o domínio + Certbot):
# PUBLIC_ORIGIN=https://SEU_DOMINIO
# API_PUBLIC_URL=https://SEU_DOMINIO/api
# ADMIN_PUBLIC_URL=https://SEU_DOMINIO/admin
# BI_PUBLIC_URL=https://SEU_DOMINIO/bi
```

Gerar segredo:

```bash
openssl rand -hex 32
```

Permissões:

```bash
chmod 640 /opt/portal-bi-tmb/.env
```

> Substitua `IP_DA_VPS` pelo IP público. Não use `https://` até o Certbot estar ativo.

---

## 5. Migrations

```bash
cd /opt/portal-bi-tmb
source .venv/bin/activate
python database/deploy/run_migrations.py
```

Confirme que rodou até a migration mais recente (ex.: `039_add_progress_snapshot_status_prazo.sql`). Em atualizações, rode **sempre** após o `git pull`.

---

## 6. Build do Admin (React)

```bash
cd /opt/portal-bi-tmb/frontend
npm ci
# Em produção o nginx serve /admin e /api no mesmo domínio:
# não é obrigatório VITE_API_URL se o front usa /api relativo.
npm run build
ls dist   # deve existir index.html
```

---

## 7. Permissões para o systemd (`www-data`)

```bash
sudo chown -R www-data:www-data /opt/portal-bi-tmb
sudo chmod -R u+rX /opt/portal-bi-tmb
# Se precisar editar como seu usuário depois:
# sudo chown -R "$USER":www-data /opt/portal-bi-tmb
# sudo chmod -R g+w /opt/portal-bi-tmb
```

Garanta que `www-data` lê `.env` e executa `.venv/bin/*`.

---

## 8. systemd — API e BI

```bash
cd /opt/portal-bi-tmb
sudo cp deploy/systemd/portal-api.service /etc/systemd/system/
sudo cp deploy/systemd/portal-bi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now portal-api portal-bi
sudo systemctl status portal-api portal-bi --no-pager
```

Logs:

```bash
sudo journalctl -u portal-api -f
sudo journalctl -u portal-bi -f
```

Teste local na VPS:

```bash
curl -s http://127.0.0.1:8000/api/health
# esperado: {"status":"ok"}
```

---

## 9. nginx

```bash
sudo cp /opt/portal-bi-tmb/deploy/nginx/portal-bi-tmb.conf \
  /etc/nginx/sites-available/portal-bi-tmb

# Ajuste server_name se quiser o domínio explícito:
# sudo nano /etc/nginx/sites-available/portal-bi-tmb
# server_name SEU_DOMINIO;

sudo ln -sf /etc/nginx/sites-available/portal-bi-tmb /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default   # se conflitar
sudo nginx -t
sudo systemctl reload nginx
```

| Path | Destino |
|------|---------|
| `/` | redirect → `/admin/` |
| `/admin/` | `frontend/dist` |
| `/api/` | uvicorn `:8000` |
| `/bi/` | Streamlit `:8501` |

Smoke HTTP:

```bash
curl -sI http://127.0.0.1/admin/
curl -s http://127.0.0.1/api/health
curl -sI http://127.0.0.1/bi/
```

---

## 10. HTTPS (Certbot) — fase 2, após domínio do cliente

**Pular na primeira publicação.** Só execute quando o DNS **A** do domínio apontar para a VPS.

```bash
sudo certbot --nginx -d SEU_DOMINIO
```

Atualize o `.env` com URLs `https://SEU_DOMINIO/...` e reinicie:

```bash
sudo systemctl restart portal-api portal-bi
```

Renovação: o timer do certbot costuma já ficar ativo (`systemctl list-timers | grep certbot`).

---

## 11. Jobs / automações (timers) — go-live

Dois timers (a cada 15 min; cada um respeita horário em **Automações** via `--if-due`):

| Unit | Job |
|------|-----|
| `portal-job-report.timer` | `report_overdue_daily --if-due` |
| `portal-job-import.timer` | `import_deliveries_daily --if-due` |

```bash
sudo cp /opt/portal-bi-tmb/deploy/systemd/portal-job-report.service /etc/systemd/system/
sudo cp /opt/portal-bi-tmb/deploy/systemd/portal-job-report.timer /etc/systemd/system/
sudo cp /opt/portal-bi-tmb/deploy/systemd/portal-job-import.service /etc/systemd/system/
sudo cp /opt/portal-bi-tmb/deploy/systemd/portal-job-import.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now portal-job-report.timer portal-job-import.timer
sudo systemctl list-timers | grep portal-job
```

### Carga inicial (one-shot, após configurar Integração API no Admin)

```bash
sudo -u www-data /opt/portal-bi-tmb/.venv/bin/python -m worker run import_deliveries_initial --force --days 20
```

### Testes manuais

```bash
sudo -u www-data /opt/portal-bi-tmb/.venv/bin/python -m worker run import_deliveries_daily --force
sudo -u www-data /opt/portal-bi-tmb/.venv/bin/python -m worker run report_overdue_daily --force
```

---

## 12. Configuração funcional pós-deploy (Admin)

1. Abrir `http://IP_DA_VPS/admin/` (depois: `https://SEU_DOMINIO/admin/`)
2. Login seed (trocar senha na sequência): `admin` / `admin123`
3. **Configurações → SMTP** — servidor padrão ativo
4. **Usuários** — filiais + `report_emails` (carga da lista operacional: `python database/deploy/update_filial_report_emails.py`)
5. **Destinatários** — e-mails gerenciais
6. **Automações** — horários do relatório **e** dos imports API
7. **Integração API** — URL, endpoint, token (sem a palavra `Bearer`), marcar padrão
8. Rodar `import_deliveries_initial --force` (one-shot)
9. Conferir timers `portal-job-report` e `portal-job-import`

---

## 13. Checklist de go-live (fase IP)

- [ ] Branch `master` na VPS
- [ ] `curl http://IP_DA_VPS/api/health` → `{"status":"ok"}`
- [ ] `http://IP_DA_VPS/admin/` carrega o SPA
- [ ] Login admin funciona; senha seed alterada
- [ ] Visualização / BI embutido abre (`/bi/`)
- [ ] Migrations aplicadas (tabelas `prb_*`)
- [ ] SMTP configurado
- [ ] Integração API salva + `import_deliveries_initial` OK
- [ ] Timers `portal-job-report` **e** `portal-job-import` ativos
- [ ] Backup Postgres agendado (ver §15)

### Checklist fase domínio (depois)

- [ ] DNS A → IP da VPS
- [ ] Certbot OK
- [ ] `.env` com `https://SEU_DOMINIO`
- [ ] `systemctl restart portal-api portal-bi`
- [ ] Smoke em HTTPS

---

## 14. Atualização (deploy rotineiro)

Script único (preferencial):

```bash
cd /opt/portal-bi-tmb
# Bash:
chmod +x deploy/update.sh   # uma vez
./deploy/update.sh

# ou CLI Python (mesmos passos; base para automação futura):
source .venv/bin/activate
python -m deploy update
```

Opções úteis:

```bash
./deploy/update.sh --branch master --with-units
python -m deploy update --skip-pull --dry-run
python -m deploy update --with-units --health-url http://127.0.0.1:8000/api/health
# Seed de clientes (idempotente; precisa do CSV no servidor):
./deploy/update.sh --skip-pull --skip-frontend --seed-clients
python -m deploy update --skip-pull --skip-frontend --no-restart --seed-clients \
  --seed-clients-csv dados/entregas_relatorio.csv
```

Equivalente manual (se preferir passo a passo):

```bash
cd /opt/portal-bi-tmb
sudo systemctl stop portal-bi portal-api   # opcional, reduz inconsistência

# se o dir for www-data, use sudo -u ou ajuste ownership temporário
git pull
source .venv/bin/activate
pip install -r requirements.txt
python database/deploy/run_migrations.py

# Após migrations 031–039 (cnpj_cliente, progressão, clientes, status_prazo):
# - Admin → Clientes (CRUD) e seed opcional: python database/deploy/seed_clients_from_csv.py
# - Progressão no BI só após novos uploads manuais (ou seed demo local)
# - Reimporte a planilha do dia no Admin para etiquetar o lote e recalcular Histórico/Progressão

cd frontend && npm ci && npm run build && cd ..

sudo systemctl start portal-api portal-bi
sudo systemctl restart portal-api portal-bi
sudo systemctl status portal-api portal-bi --no-pager
curl -s http://127.0.0.1:8000/api/health
```

Se mudou units/nginx:

```bash
sudo cp deploy/systemd/*.service /etc/systemd/system/
sudo cp deploy/systemd/*.timer /etc/systemd/system/ 2>/dev/null || true
sudo cp deploy/nginx/portal-bi-tmb.conf /etc/nginx/sites-available/portal-bi-tmb
sudo systemctl daemon-reload
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl restart portal-api portal-bi
```

---

## 15. Backup e rollback (mínimo)

### Backup Postgres

```bash
sudo -u postgres pg_dump portal_bi_tmb | gzip > ~/backup-portal_bi_tmb-$(date +%F).sql.gz
```

Agendar (exemplo diário 02:30):

```bash
sudo crontab -e
# 30 2 * * * /usr/bin/pg_dump -U postgres portal_bi_tmb | gzip > /var/backups/portal_bi_tmb-$(date +\%F).sql.gz
```

### Rollback de código

```bash
cd /opt/portal-bi-tmb
git log --oneline -5
git checkout <commit-ou-tag-anterior>
# repita §14 a partir de pip/migrate/build/restart
```

Migrations SQL são incrementais — **não** reverta migration já aplicada sem plano explícito de DBA.

---

## 16. Troubleshooting rápido

| Sintoma | Onde olhar |
|---------|------------|
| API down | `journalctl -u portal-api -n 80` |
| BI em branco / WS | conf nginx `Upgrade`; `journalctl -u portal-bi` |
| 502 em `/api` | API no ar? `curl 127.0.0.1:8000/api/health` |
| Admin 404 assets | `frontend/dist` existe? `alias` nginx |
| Erro DB | `DATABASE_URL`, senha, `pg_isready`, grants |
| Job não dispara | `systemctl list-timers`; Automações no Admin; `--force` manual |
| BI Operacional vazio / “nenhum lote ativo” | Reimporte a planilha (marca `dataset_batch_id`) ou rode sync API |
| Histórico do dia desatualizado após planilha | Import deve usar `capture_replace`; confirme migration e reimporte |
| 401 TMS Elite | token sem prefixo `Bearer `; config padrão ativa |

---

## Local (dev) — referência

```bash
# API
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8001

# BI
.\.venv\Scripts\python.exe -m streamlit run app.py --server.baseUrlPath bi --server.port 8501

# Admin
cd frontend && npm run dev
# http://localhost:5173/admin/
```

Worker: ver [`servico-jobs.md`](servico-jobs.md).
