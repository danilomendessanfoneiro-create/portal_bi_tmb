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
Código validado em local (coleta lote #34, relatórios e e-mails técnicos). Branch de trabalho `develop`; publicação continua em `master`. Runbook detalhado: `docs/release-automacoes-monitoramento.md`.

## Abordagem
Merge/push para `master` → backup → `./deploy/update.sh --branch master --with-units` → `.env` TECH_SMTP → smoke Admin/timers. Alternativa “só rsync sem git” descartada: o script já cobre pip, Playwright, migrate e build.

## Passos
- [ ] Commit/merge das mudanças em `master` (sem secrets / sem `.env`)
- [ ] Backup `pg_dump` na VPS
- [ ] `./deploy/update.sh --branch master --with-units`
- [ ] Confirmar migrations `040`–`042` em `prb_schema_migrations`
- [ ] Preencher `TECH_SMTP_*` no `.env` da VPS e restart serviços
- [ ] Smoke `/api/health`, `/admin/` Automações (dias + 4 cards)
- [ ] Ativar robôs desejados; dry-run TMS; conferir 1 e-mail técnico

## Riscos & Mitigações
- Jobs visíveis podem nascer/ficar ativos após seed local → na VPS conferir `enabled` antes do horário
- Sem `TECH_SMTP_PASSWORD` o negócio roda sem alerta técnico → checklist obrigatório
- Playwright/Chromium faltando → `update.sh` já instala no passo pip

## Questões em aberto
- Confirmar se a VPS puxa de `origin/master` ou outro remoto
- Horários de produção desejados (manter 05:00 / 08:00?)
