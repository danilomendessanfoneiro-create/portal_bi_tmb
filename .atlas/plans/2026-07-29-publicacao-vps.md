---
title: Publicação do Portal BI na VPS
created: 2026-07-29
status: draft
tags: [deploy, vps, nginx, systemd, hostinger]
related: ["docs/deploy-vps.md", "docs/topologia-hibrida.md", "docs/servico-jobs.md", "deploy/"]
---

# Plano: Publicação do Portal BI na VPS

## Objetivo
Publicar o Portal BI TMB (Admin React + FastAPI + Streamlit + Postgres + jobs) na VPS Hostinger, inicialmente por **IP (HTTP)**, depois HTTPS quando o cliente liberar o domínio. Pronto = smoke checks OK em `/admin`, `/api/health`, `/bi`, timers de relatório **e import API** ativos.

## Contexto
- Código-alvo: `/opt/portal-bi-tmb` (Ubuntu).
- Artefatos: `deploy/systemd/*`, `deploy/nginx/portal-bi-tmb.conf`, `database/deploy/run_migrations.py`.
- Runbook: [`docs/deploy-vps.md`](../../docs/deploy-vps.md).
- Topologia: [`docs/topologia-hibrida.md`](../../docs/topologia-hibrida.md).

### Decisões fechadas (2026-07-29)
- **Acesso:** até o domínio do cliente, publicar pelo **IP da VPS** (HTTP). Certbot/HTTPS só depois do DNS.
- **Branch de publicação:** **`master`** (a criar a partir do código estável; deploys na VPS fazem checkout/pull de `master`).
- **Jobs no go-live:** sim — relatório diário **e** importações API (`import_deliveries_initial` one-shot + `import_deliveries_daily` via timer `--if-due`).

## Abordagem
Primeiro deploy completo em HTTP/IP; TLS em fase posterior. Deploys seguintes = `git pull` em `master` + migrate + rebuild frontend + restart. Jobs: timers a cada 15 min com `--if-due` (horário vem das Automações no Admin).

## Passos
- [ ] 0. Pré-requisitos: SSH, IP da VPS, Postgres, Node 20+, Python 3.11+ (domínio **adiado**)
- [ ] 0b. Criar branch `master` de publicação e push no remoto
- [ ] 1. Provisionar SO (nginx, build-essential, git; certbot pode instalar já, usar depois)
- [ ] 2. Clonar repo e `git checkout master`
- [ ] 3. venv + `pip install -r requirements.txt`
- [ ] 4. `.env` com `PUBLIC_*` em `http://IP_DA_VPS` (sem https ainda)
- [ ] 5. Migrations
- [ ] 6. Build Admin (`npm ci` + `npm run build`)
- [ ] 7. Ownership `www-data` + `portal-api` / `portal-bi`
- [ ] 8. nginx (server_name `_` ou IP) + reload
- [ ] 9. **Adiado:** Certbot HTTPS quando o cliente liberar o domínio → atualizar `.env` + restart
- [ ] 10. Timers: `portal-job-report.timer` + `portal-job-import.timer`
- [ ] 11. Smoke: `http://IP/api/health`, `/admin/`, `/bi/`
- [ ] 12. Admin: SMTP + Integração API + senha seed; rodar `import_deliveries_initial --force`
- [ ] 13. Confirmar Automações (horários) e 1 ciclo `--if-due` dos jobs
- [ ] 14. Quando domínio chegar: DNS → Certbot → URLs https no `.env` → restart

## Riscos & Mitigações
- `.env` com porta 5433 → usar `:5432` na VPS.
- Acesso só por IP: cookies/URLs públicas devem bater com `http://IP` → conferir `.env`.
- Senha seed → trocar no primeiro login.
- `master` desatualizada vs `develop` → merge/rebase consciente antes de cada publicação.
- Import sem config API → falha 401/config; validar Integração API antes do timer.

## Questões em aberto
- Backup automático do Postgres (cron/`pg_dump`) já existe na Hostinger?
- IP público definitivo da VPS para documentar no `.env` de go-live?
