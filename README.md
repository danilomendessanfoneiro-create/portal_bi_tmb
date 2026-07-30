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
| [docs/integracao-api-tmselite.md](docs/integracao-api-tmselite.md) | Integração TMS (futura) |
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
- **Configurações → Automações** — horários amigáveis (sem IDs técnicos):
  - Envio diário das filiais
  - Relatório gerencial (diário / semanal / mensal — parametrização; geração semanal/mensal futura)

### BI (Streamlit `/bi`)

- Dashboard de entregas a partir de `dados/entregas_relatorio.csv` (`limpeza.py`).
- Filtros na sidebar; modo embed sem navegação duplicada.
- Segregação por filial alinhada ao perfil do usuário.

### Relatórios por e-mail (worker)

Job único `report_overdue_daily` com duas fases (fonte: **`prb_deliveries`** via API):

1. **Filiais** — um HTML por e-mail cadastrado no usuário filial; só dados daquela filial.
2. **Gerencial** — HTML consolidado aos destinatários administrativos (assunto/saudação com o **nome do destinatário**).

Características:

- Corpo **HTML** (compatível Outlook/Gmail), **sem anexo**.
- Seções: notas em atraso e notas que vencem hoje.
- Colunas: Nota Fiscal, Cliente, Cidade, Dt. Agendamento, Ult. Motorista, Dias em atraso (vazios → string vazia, sem `NaT`/`nan`).
- Filial sem e-mail: aviso no log e segue.
- CSV local em `storage/reports/` apenas para auditoria.
- Idempotência por automação + data (`prb_job_runs`).

### Persistência (PostgreSQL)

Migrations incrementais em `database/migrations/` (até `019`), padrão `prb_*` + `_audit`:

- Usuários, SMTP, destinatários, execuções de job, automações (`display_name`, `frequency`, `weekday`, `day_of_month`)
- Integração API (`prb_api_settings`), entregas (`prb_deliveries`), logs (`prb_integration_logs`)

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
# API (Vite proxy aponta para :8001)
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8001

# BI
.\.venv\Scripts\python.exe -m streamlit run app.py --server.baseUrlPath bi --server.port 8501

# Admin
cd frontend
npm install
npm run dev
```

Abrir: **http://localhost:5173/admin/**  
Login seed (se não alterado): `admin` / `admin123`

### Worker de relatório / importação

```bash
.\.venv\Scripts\python.exe -m worker list
.\.venv\Scripts\python.exe -m worker run import_deliveries_initial --dry-run
.\.venv\Scripts\python.exe -m worker run import_deliveries_daily --force
.\.venv\Scripts\python.exe -m worker run report_overdue_daily --dry-run
```

Configurar antes: Admin → Integração API (URL + Bearer). Detalhes: [docs/integracao-api-tmselite.md](docs/integracao-api-tmselite.md).

### Testes

```bash
.\.venv\Scripts\python.exe -m pytest tests -q
```

## Estrutura principal

```
app/           # domínios, services, repositories, API FastAPI, controllers Streamlit
frontend/      # admin React (Vite)
worker/        # CLI de jobs (relatório diário)
database/      # migrations e runner
deploy/        # nginx + systemd
docs/          # documentação operacional
tasks/         # PRDs
dados/         # planilha de entregas (fonte atual do BI/jobs)
```

## Branch e remoto

- Remoto: `origin` → `https://github.com/danilomendessanfoneiro-create/portal_bi_tmb.git`
- Desenvolvimento contínuo: branch `develop`
