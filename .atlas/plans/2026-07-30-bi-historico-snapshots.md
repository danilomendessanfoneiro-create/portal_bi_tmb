---
title: Módulo BI histórico — snapshots diários de atrasos
created: 2026-07-30
status: draft
tags: [bi, historico, snapshot, arquitetura]
related: ["worker/jobs/report_overdue_daily_impl.py", "limpeza.py", "docs/servico-jobs.md", "app/services/macro_delivery_rules.py", "tasks/prd-bi-historico-snapshots.md"]
---

# Plano: Módulo BI histórico — snapshots diários de atrasos

## Objetivo
Complementar o Portal BI com um **dashboard histórico** (Streamlit) baseado em snapshots diários imutáveis da situação de atrasos (antes do e-mail gerencial), com os **mesmos filtros do BI atual** e o mesmo AccessScope. Pronto = snapshot 1×/dia + gráfico barras + script de demo fake 30 dias.

PRD: [`tasks/prd-bi-historico-snapshots.md`](../../tasks/prd-bi-historico-snapshots.md).

## Contexto
- BI atual = foto operacional de `prb_deliveries` + regras macros (`processar_entregas`).
- Relatório = `report_overdue_daily`; snapshot entra **uma vez no job**, antes de qualquer e-mail.
- Filtros do histórico = **os mesmos do BI existente** (filial, cliente, cidade, situação, período, tolerância, busca). “Transportadora” era só exemplo — **não** criar filtro novo.

### Decisões fechadas (2026-07-30)
- **UI:** Streamlit, no dashboard atual (nova seção/aba “Histórico”).
- **Histórico real:** a partir do go-live / primeiros jobs (sem backfill fiel do passado operacional).
- **Demo/teste:** script dedicado gera **dados fake dos últimos 30 dias** (não misturar com produção real; actor/`source` = `seed-demo`).
- **Filtros:** manter todos os do BI atual; sem filtro extra inventado.
- **Captura:** uma vez por `business_date` no job, antes dos e-mails.

## Abordagem

### Arquitetura recomendada
**Snapshot run + fato no grain da entrega atrasada.**

```
prb_deliveries (operacional)
        │
processar_entregas
        │
report_overdue_daily  ──►  SnapshotService (1×/dia, skip se existe)
        │                         │
        ▼                         ▼
   e-mails                    prb_bi_snapshot_run
                              prb_bi_snapshot_overdue
                                      │
                              Streamlit — seção Histórico
                              (mesmos filtros + AccessScope)
```

Demo: `python database/deploy/seed_bi_snapshot_demo.py --days 30` (ou `python -m worker run …`) popula runs/fatos sintéticos para apresentação ao cliente.

### Modelagem (`prb_*` + audit)
1. **`prb_bi_snapshot_run`** — UNIQUE(`business_date`), `captured_on`, `rule_version`, `total_overdue`, `source` (`job` \| `seed-demo`), audit fields.
2. **`prb_bi_snapshot_overdue`** — fato por entrega atrasada (dims de filtro do BI), UNIQUE(`snapshot_run_id`, `remessa_numero`), audit.
3. **Fase posterior:** `prb_bi_snapshot_kpi` para métricas genéricas.

### Anti-duplicidade
- Captura idempotente: se já existe run do dia → skip.
- `--force` no e-mail **não** regrava snapshot.
- Script demo: flag `--replace-demo` apaga só runs `source=seed-demo` antes de regenerar.

## Passos
- [x] Fase 0 — Decisões: Streamlit; sem backfill real; seed fake 30d; filtros = BI atual
- [x] Fase 1 — Migrations `020+` (run + overdue + audits)
- [x] Fase 2 — `SnapshotService` + repositório + idempotência
- [x] Fase 3 — Hook no `report_overdue_daily` antes dos e-mails
- [x] Fase 4 — Queries agregadas + AccessScope + filtros do BI
- [x] Fase 5 — Seção Histórico no Streamlit (barras 7/15/30/60/90/custom)
- [x] Fase 6 — Script `seed_bi_snapshot_demo.py` (30 dias fake, `--replace-demo`)
- [x] Fase 7 — Testes + docs + migrate VPS

## Riscos & Mitigações
- Misturar fake com prod no cliente → `source=seed-demo` + comando para limpar só demo.
- Slider de tolerância no histórico → snapshot grava regra do relatório; tolerância continua só no BI operacional (documentar na UI Histórico).
- Volume fake irreal → seed usa filiais/clientes/cidades amostrados da base atual quando existir.

## Questões em aberto
- (nenhuma bloqueante) — pronto para implementação quando autorizado.
