# Topologia híbrida — Portal BI TMB

## Fluxo (Opção 1 — portal shell)

```
Navegador
   │
   ▼
nginx (HTTPS)  — ou Vite proxy em dev
   ├── /admin/*           → React (shell: menu + auth + configurações)
   │     └── /visualizacao → iframe same-origin → /bi/?embed=true
   ├── /api/*             → FastAPI (VPS :8000 | local tipicamente :8001)
   └── /bi/*              → Streamlit ( :8501 , baseUrlPath=bi)
          │                 modo embed: sem sidebar de navegação própria
          ▼
     PostgreSQL (portal_bi_tmb) — tabelas prb_*
```

Futuro: trocar o alvo do iframe de Streamlit para Apache Superset sem mudar o shell.

## Autenticação unificada

1. Login em `/admin` chama `POST /api/auth/login`.
2. API devolve JWT; React guarda em `localStorage` + cookie `portal_token` (path=/).
3. Iframe do BI abre `/bi/?embed=true&token=…` (mesmo host em prod/dev com proxy).
4. Streamlit valida o JWT e renderiza só o dashboard (sem menu duplicado).
5. Perfil **filial** restringe dados à própria filial na camada de serviço (`AccessScopeService`).

## Módulos do admin

| Rota | Função |
|------|--------|
| Usuários | CRUD; e-mails de relatório por filial (`report_emails`) |
| Configurações → SMTP | Servidor de e-mail padrão |
| Configurações → Destinatários | Destinatários gerenciais |
| Configurações → Automações | Horários filiais + gerencial |
| Visualização | BI embutido |

## Processos na VPS

| Serviço | Unit | Porta interna |
|---|---|---|
| API | `portal-api.service` | 8000 |
| BI | `portal-bi.service` | 8501 |
| Job relatório | `portal-job-report.timer` | CLI `report_overdue_daily --if-due` |
| Job import API | `portal-job-import.timer` | CLI `import_deliveries_daily --if-due` |
| Admin | nginx static | — |
| DB | postgresql | 5432 |

Ver também: [`docs/deploy-vps.md`](deploy-vps.md), [`docs/servico-jobs.md`](servico-jobs.md) e pasta `deploy/`.
