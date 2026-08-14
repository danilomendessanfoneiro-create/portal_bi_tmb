---
title: Teste local dos jobs e monitoramento técnico
created: 2026-08-14
status: done
tags: [qa, jobs, smtp]
related: ["tasks/prd-reestruturacao-automacoes-monitoramento.md", "docs/servico-jobs.md"]
---

# Plano: Teste local dos jobs e monitoramento técnico

## Objetivo
Validar na stack local (API :8003, Admin :5173, BI :8501) que os robôs visíveis respeitam ativo+dia+horário e que cada execução success/failed grava `prb_job_runs` e dispara o e-mail técnico.

## Contexto
PRD de automações já implementado (US-001…009). Jobs visíveis nasceram `enabled=false`; o usuário ativou os 4 na UI. Hoje é sexta (dia 5), depois das 08:00 — `--if-due` dispara. `--dry-run` não grava run nem e-mail técnico. `--force` ignora idempotência do dia. SMTP técnico via `TECH_SMTP_*`. Destinatário: `jeverson.abreu@gmail.com`.

Relatórios de atraso (`report_*`) enviam e-mail operacional — só rodar com ok explícito.

## Abordagem
Smoke SMTP → coleta TMS `--force` (run + e-mail técnico) → confirmar idempotência → decidir relatórios.

## Passos
- [x] Reiniciar API (:8003), Streamlit (:8501) e Admin Vite (:5173)
- [x] Conferir migrations 041/042 e `TECH_SMTP_PASSWORD` no `.env`
- [x] Listar settings/runs; usuário ativou os 4 jobs
- [x] `--if-due` TMS/report com jobs desligados → skip (rodado antes)
- [x] GET schedules só 4 jobs visíveis
- [x] `TECH_SMTP_PASSWORD` preenchido; SMTP carrega
- [x] Smoke `notify_visible_robot_run` → e-mail técnico sem exception
- [x] `--force` TMS → lote #34 (2394 linhas), run #32 `duration_ms=65438`
- [x] `--if-due` TMS após sucesso do dia → skipped idempotente
- [x] Relatórios `--if-due` — filiais 13, clientes 7, gerencial 2; runs #33–35 com duration_ms; 0 erros

## Riscos & Mitigações
- Relatórios `--if-due` com jobs ativos → e-mails reais de atraso → executado com ok do usuário
- Coleta `--force` gera lote novo → já executado (#34)

## Questões em aberto
- Conferir na caixa os e-mails operacionais + 3 técnicos (filiais/clientes/gerencial)
