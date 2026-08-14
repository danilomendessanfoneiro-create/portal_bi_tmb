# Portal BI TMB

Portal de BI e administração da operação logística TMB: visualização de entregas (Streamlit), painel admin (React) e API (FastAPI), com envio automático de relatórios por e-mail.

## Arquitetura

```
Navegador
   │
   ▼
Vite (dev) / nginx (prod)
   ├── /admin/*  → React (login, usuários, SMTP, destinatários, automações, BI embutido)
   ├── /api/*    → FastAPI
   └── /bi/*     → Streamlit (dashboard; embed no admin via iframe)
          │
          ▼
     PostgreSQL (tabelas prb_*)
```

Documentação detalhada:

| Documento | Conteúdo |
|-----------|----------|
| [docs/topologia-hibrida.md](docs/topologia-hibrida.md) | Topologia, auth JWT, embed do BI |
| [docs/deploy-vps.md](docs/deploy-vps.md) | Deploy na VPS |
| [docs/servico-jobs.md](docs/servico-jobs.md) | Worker de relatórios e automações |
| [docs/importacao-manual-planilha.md](docs/importacao-manual-planilha.md) | Upload/validação/importação manual |
| [docs/paridade-lote-ativo-macros.md](docs/paridade-lote-ativo-macros.md) | Lote ativo e paridade com macros Excel |
| [docs/analise-prazo-considerado.md](docs/analise-prazo-considerado.md) | Regra de atraso (Dt. Prazo Atual) |
| [docs/responsividade-mobile.md](docs/responsividade-mobile.md) | Breakpoints, drawer, PWA, checklist mobile |
| [docs/integracao-api-tmselite.md](docs/integracao-api-tmselite.md) | Integração TMS Elite |
| [app/api/README.md](app/api/README.md) | Endpoints da API |

## Funcionalidades implementadas

### Autenticação e perfis

- Login unificado (JWT) no admin React; o BI Streamlit valida o mesmo token (`?token=` / cookie).
- Perfis: **admin** (visão completa) e **filial** (somente dados da própria filial — `AccessScopeService`).
- CRUD de usuários no admin (não mais no Streamlit).

### Administração (React `/admin`)

- **Usuários** — login, perfil, filial, ativo/inativo; para perfil filial, campo **E-mails do relatório** (múltiplos separados por `;`, validados).
- **Configurações → SMTP** — host, credenciais, remetente, SMTP padrão.
- **Configurações → Destinatários** — e-mails gerenciais (flags diário / semanal / mensal).
- **Configurações → Automações** — 4 robôs visíveis (sem IDs técnicos / sem API):
  - Coleta da planilha TMS Elite (05:00 seed; dias da semana; credenciais)
  - Envio diário das filiais / clientes / gerencial (08:00 seed)
  - Regra: **ativo + dias da semana + horário**; feedback de sucesso/erro ao salvar
- Menu **Integração API** oculto (código/backend permanecem)
### BI (Streamlit `/bi`)

- Dashboard **Operacional** a partir do **lote ativo** em `prb_deliveries` (`limpeza.processar_entregas`).
- Lote ativo = última planilha importada; senão última sync API (ver [docs/paridade-lote-ativo-macros.md](docs/paridade-lote-ativo-macros.md)).
- Aba **Histórico** com snapshots diários + drill-down do dia.
- Filtros na sidebar; modo embed sem navegação duplicada.
- Segregação por filial alinhada ao perfil do usuário.
- Atraso alinhado às macros Excel (`Dt. Prazo Atual` + exclusão das 5 contas em `cliente_conta`).

### Relatórios por e-mail (worker)

Job `report_overdue_daily` com três fases (fonte: **lote ativo** em `prb_deliveries`):

1. **Filiais** — HTML por e-mail do usuário filial.
2. **Clientes** — HTML por CNPJ cadastrado em Clientes.
3. **Gerencial** — consolidado aos destinatários administrativos.

Características:

- Corpo **HTML**, **sem anexo**; CSV só em `storage/reports/` (auditoria).
- Idempotência por automação + data (`prb_job_runs` com `duration_ms` / `error_step`).
- Disparo manual no Admin — **não** automático após import.
- Monitoramento técnico separado (`TECH_SMTP_*` no `.env`): e-mail após success/failed dos robôs visíveis, com métricas e motivo da falha.

Coleta diária da planilha: `fetch_tmselite_spreadsheet` (Playwright). Detalhes: [docs/servico-jobs.md](docs/servico-jobs.md).

### Persistência (PostgreSQL)

Migrations incrementais em `database/migrations/` (até `042`), padrão `prb_*` + `_audit`:

- Usuários, SMTP, destinatários, execuções de job (`duration_ms`, `error_step`)
- Automações (`display_name`, `run_weekdays`, horário, credenciais TMS cifradas)
- Integração API (`prb_api_settings`), entregas, snapshots BI, importação manual, lote ativo

## Desenvolvimento local

### Pré-requisitos

- Python 3.11+ (venv), Node.js, PostgreSQL
- Copiar `.env.example` → `.env` e ajustar `DATABASE_URL` / `JWT_SECRET`

### Migrations

```bash
.\.venv\Scripts\python.exe database\deploy\run_migrations.py
```

### Subir a stack (3 terminais)

```bash
# API (Vite proxy aponta para :8003 — evita listeners fantasmas de portas antigas no Windows)
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8003

# BI
.\.venv\Scripts\python.exe -m streamlit run app.py --server.baseUrlPath bi --server.port 8501

# Admin
cd frontend
npm install
npm run dev
```

Abrir: **http://localhost:5173/admin/**  
Login seed (se não alterado): `admin` / `admin123`

### Worker de relatório / coleta / importação

```bash
.\.venv\Scripts\python.exe -m worker list
.\.venv\Scripts\python.exe -m worker run fetch_tmselite_spreadsheet --dry-run
.\.venv\Scripts\python.exe -m worker run fetch_tmselite_spreadsheet --force
.\.venv\Scripts\python.exe -m worker run report_overdue_daily --if-due
.\.venv\Scripts\python.exe -m worker run report_overdue_daily --dry-run
```

SMTP técnico: `TECH_SMTP_*` no `.env` ([`.env.example`](.env.example)).  
Deploy VPS desta release: [docs/release-automacoes-monitoramento.md](docs/release-automacoes-monitoramento.md).  
Jobs: [docs/servico-jobs.md](docs/servico-jobs.md). API legado: [docs/integracao-api-tmselite.md](docs/integracao-api-tmselite.md).

### Testes

```bash
.\.venv\Scripts\python.exe -m pytest tests -q
```

## Estrutura principal

```
app/           # domínios, services, repositories, API FastAPI, controllers Streamlit
frontend/      # admin React (Vite)
worker/        # CLI de jobs (coleta TMS, relatório, import API)
database/      # migrations e runner (até 042)
deploy/        # nginx + systemd + update.sh
docs/          # documentação operacional + release notes
tasks/         # PRDs
dados/         # planilha de entregas (fonte atual do BI/jobs)
```

## Branch e remoto

- Remoto: `origin` → `https://github.com/danilomendessanfoneiro-create/portal_bi_tmb.git`
- Desenvolvimento contínuo: branch `develop`
