---
title: Deploy VPS — automações, TMS e monitoramento
created: 2026-08-14
status: active
tags: [deploy, vps, jobs]
related:
  - "docs/release-automacoes-monitoramento.md"
  - "docs/deploy-vps.md"
  - "tasks/prd-reestruturacao-automacoes-monitoramento.md"
---

# Plano: Deploy VPS — automações, TMS e monitoramento

## Objetivo
Publicar na VPS (`master` → `/opt/portal-bi-tmb`) as automações por dia da semana, coleta TMS Elite, e-mail técnico enriquecido e migrations 040–042. Pronto = health OK, Automações com 4 cards, timers ativos, `TECH_SMTP_*` preenchido.

## Contexto
Código em `9c5195a` no remoto. Deploy VPS feito em 2026-08-14: migrations OK, health OK, timers ativos, Playwright em `/opt/ms-playwright`. `TECH_SMTP_*` keys no `.env`; **PASSWORD ainda vazia**. Os 4 robôs ficaram `enabled=false` (seed).

## Abordagem
Backup → sync `origin/master` → update.sh (pip/playwright/migrate/build/units) → Chromium para www-data → checklist Admin.

## Passos
- [x] Commit/merge em `master`
- [x] Backup `pg_dump` na VPS
- [x] Deploy `9c5195a` + units
- [x] Migrations `040`–`042`
- [x] Smoke `/api/health`, `/admin/`, `/bi/`
- [x] Timers `portal-job-import` / `portal-job-report`
- [x] Playwright path `/opt/ms-playwright` (www-data)
- [ ] Preencher `TECH_SMTP_PASSWORD` no `.env` VPS + restart se precisar
- [ ] Ativar automações desejadas; credenciais TMS; dry-run coleta

## Riscos & Mitigações
- Sem `TECH_SMTP_PASSWORD` → jobs ok, e-mail técnico ignorado
- Robôs desativados no seed → ativar só o necessário no Admin

## Questões em aberto
- Colar senha de app Gmail em `TECH_SMTP_PASSWORD` na VPS
