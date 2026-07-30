# PRD: Módulo BI Histórico — Snapshots Diários de Atrasos

## Introduction

O Portal BI atual mostra apenas a **situação operacional do momento** (entregas em atraso derivadas de `prb_deliveries` + regras macros). O cliente também recebe diariamente um relatório gerencial consolidado, mas **não consegue ver a evolução** do volume de atrasos ao longo do tempo.

Esta feature adiciona uma **camada histórica complementar**: antes do envio do relatório (`report_overdue_daily`), o sistema grava um **snapshot imutável** das entregas em atraso daquele dia. Um novo dashboard no **Streamlit** (junto ao BI atual) permite visualizar a evolução em gráfico de barras, com os **mesmos filtros e o mesmo controle de acesso** (admin × filial).

**Decisões fechadas:**
- UI no Streamlit (seção/aba **Histórico** no dashboard atual).
- Grain do snapshot = **entrega atrasada** (não só total/dia), para os filtros funcionarem.
- Captura **1× por `business_date`**, no job de relatório, **antes** de qualquer e-mail; idempotente (não sobrescreve).
- Sem backfill fiel do passado operacional; para demo/teste: script de **dados fake dos últimos 30 dias** (`source=seed-demo`).
- Filtros = **todos os do BI existente** (filial, cliente, cidade, situação, período, tolerância, busca). Sem filtro novo inventado.
- Tabelas `prb_*` + `_audit` com campos de auditoria padrão.

Referência de arquitetura: `.atlas/plans/2026-07-30-bi-historico-snapshots.md`.

## Goals

- Persistir snapshot diário imutável das entregas em atraso (run + fatos)
- Integrar captura ao `report_overdue_daily` sem alterar o conteúdo dos e-mails
- Dashboard histórico Streamlit: barras (dias × qtde atrasos), janelas 7/15/30/60/90/custom
- Respeitar `AccessScopeService` (filial só vê a própria; admin vê consolidado/filtros)
- Script de seed demo (`seed-demo`) para os últimos 30 dias, isolável da produção
- Preparar extensão futura de KPIs sem remodelar o core (fase opcional `prb_bi_snapshot_kpi`)

## User Stories

### US-001: Schema de snapshots históricos
**Description:** As a developer, I want `prb_bi_snapshot_run` and `prb_bi_snapshot_overdue` (+ audits) so that daily overdue history is stored immutably and independently from operational deliveries.

**Acceptance Criteria:**
- [ ] Migration `020_create_prb_bi_snapshot_run.sql` com `business_date` UNIQUE, `captured_on`, `source_job_id`, `source_run_id` nullable, `rule_version`, `total_overdue`, `total_value_overdue` nullable, `source` (`job` | `seed-demo`), `created_by/on`, `modified_by/on`, `enabled`
- [ ] Migration `021_create_prb_bi_snapshot_run_audit.sql` no padrão do projeto
- [ ] Migration `022_create_prb_bi_snapshot_overdue.sql` com FK para run, dims de filtro do BI (`remessa_numero`, `nro_entrega`, `nota_fiscal`, `filial`, `cliente`, `cidade_entrega`, `uf_entrega`, `status`, `motorista`, `dias_atraso`, `valor_total`, `prazo_considerado`, `status_prazo`, `business_date`), UNIQUE(`snapshot_run_id`, `remessa_numero`), audit fields + `enabled`
- [ ] Migration `023_create_prb_bi_snapshot_overdue_audit.sql`
- [ ] Índices em `(business_date)`, `(filial, business_date)`, `(cliente, business_date)`
- [ ] Runner `database/deploy/run_migrations.py` aplica as novas migrations sem erro
- [ ] Tests pass

### US-002: SnapshotService idempotente
**Description:** As an operador, I want a service that captures today's overdue set once so that re-running the report does not duplicate or rewrite history.

**Acceptance Criteria:**
- [ ] `app/services/bi_snapshot_service.py` (ou nome equivalente) com `capture_if_absent(business_date, overdue_df, *, actor, source_job_id, source_run_id)`
- [ ] Se já existe run para `business_date` → retorna skipped sem INSERT
- [ ] Se não existe → INSERT run + linhas do fato a partir do DataFrame `atrasado` (mesmas regras do relatório / macros)
- [ ] `rule_version` constante documentada (ex. `macros-v1`)
- [ ] Repository dedicado; sem UPDATE de fatos após insert
- [ ] Unit tests: primeiro capture grava; segundo no mesmo dia skip; UNIQUE respeitado
- [ ] Tests pass

### US-003: Hook no job report_overdue_daily
**Description:** As an operador, I want the snapshot written before any report e-mail so that the historical photo matches the managerial report of that day.

**Acceptance Criteria:**
- [ ] Em `report_overdue_daily_impl`, após `_load_frames` / overdue, chamar `capture_if_absent` **antes** das fases de e-mail A/B
- [ ] Falha no snapshot não deve corromper o envio se for política definida: documentar e implementar (preferência: log + continua e-mail, ou falha o job — escolher e testar; default: **log error + continua e-mail**, métrica `snapshot_status`)
- [ ] `--force` no job **não** regrava snapshot existente
- [ ] Métricas do JobResult incluem `snapshot=created|skipped|failed`
- [ ] Tests pass

### US-004: Consultas históricas com escopo e filtros
**Description:** As a developer, I want query APIs/repos that aggregate overdue counts by day with BI filters and AccessScope so the dashboard can reuse existing access rules.

**Acceptance Criteria:**
- [ ] Repository/service: agrega `COUNT(*)` por `business_date` a partir de `prb_bi_snapshot_overdue`, filtros opcionais filial/cliente/cidade (e demais dims alinhadas ao BI)
- [ ] Admin: pode filtrar qualquer filial; filial: obrigatório restringir à `viewer.branch` (nunca vaza outra filial)
- [ ] Janela de datas: início/fim explícitos (usados pelos presets 7/15/30/60/90/custom)
- [ ] Não lê `prb_deliveries` para o gráfico histórico
- [ ] Tests pass

### US-005: Dashboard Histórico no Streamlit
**Description:** As a usuário do BI, I want a Histórico section on the current Streamlit dashboard so that I can see overdue evolution over time with the same filters I already use.

**Acceptance Criteria:**
- [ ] Seção/aba **Histórico** no fluxo Streamlit atual (mesmo auth / `AccessScopeService` / sidebar de filtros do BI)
- [ ] Gráfico de barras: X = dias (`business_date`), Y = quantidade de entregas em atraso (após filtros)
- [ ] Seletor de janela: 7, 15, 30, 60, 90 dias e período personalizado (date range)
- [ ] Filtros existentes do BI aplicados ao gráfico histórico (filial conforme perfil; cliente; cidade; demais que fizerem sentido no fato — situação/tolerância: documentar na UI se não se aplicam ao fato histórico da mesma forma)
- [ ] Estado vazio amigável quando não houver snapshots no período
- [ ] Typecheck passes
- [ ] Verify in browser

### US-006: Script de dados fake (demo 30 dias)
**Description:** As a developer, I want a seed script that generates fake snapshots for the last 30 days so we can demo the historical dashboard to the client without real backfill.

**Acceptance Criteria:**
- [ ] Script `database/deploy/seed_bi_snapshot_demo.py` com `--days` (default 30) e `--replace-demo`
- [ ] `--replace-demo` remove apenas runs/fatos com `source=seed-demo` antes de regenerar
- [ ] Gera variação diária plausível de contagens; quando possível, reutiliza filiais/clientes/cidades existentes em `prb_deliveries`
- [ ] Não apaga snapshots `source=job`
- [ ] Documentado em `docs/` (como rodar local/VPS) e no plano
- [ ] Documentation complete

### US-007: Testes e documentação
**Description:** As a developer, I want tests and docs so the historical module is operable in local and VPS the same way as other jobs.

**Acceptance Criteria:**
- [ ] Testes cobrindo idempotência do snapshot, escopo filial e agregação filtrada
- [ ] Atualizar `docs/servico-jobs.md` (ou doc dedicado) com fluxo snapshot + seed demo
- [ ] Mencionar no `docs/deploy-vps.md` ou runbook: migrate `020+` + seed opcional
- [ ] Documentation complete

## Functional Requirements

- FR-1: O sistema deve gravar no máximo **um** `prb_bi_snapshot_run` por `business_date`
- FR-2: O snapshot deve conter uma linha em `prb_bi_snapshot_overdue` por entrega classificada como `atrasado` no momento da captura (regras macros / mesmo critério do relatório)
- FR-3: A captura deve ocorrer no job `report_overdue_daily` **antes** do envio de e-mails
- FR-4: Reexecução do job no mesmo dia não deve alterar fatos já gravados
- FR-5: O dashboard histórico deve agregar contagem por dia respeitando filtros e perfil (admin/filial)
- FR-6: Presets de janela 7/15/30/60/90 dias e range custom
- FR-7: Script demo gera 30 dias fake com `source=seed-demo` e opção de regenerar só demo
- FR-8: Tabelas seguem padrão `prb_*`, auditoria `_audit`, campos `created_by/on`, `modified_by/on`, `enabled`
- FR-9: Histórico é complementar; não substitui KPIs/tabelas do BI operacional

## Non-Goals

- Backfill fiel a partir da base operacional atual para datas passadas
- Substituir ou alterar o conteúdo HTML dos e-mails do relatório
- Novo filtro “transportadora” ou outros filtros além dos do BI atual
- Modelo estrela completo / data warehouse separado nesta versão
- Tabela `prb_bi_snapshot_kpi` genérica (fica para fase posterior, apenas preparada na arquitetura)
- Reescrita de snapshot via `--force` do relatório
- Dashboard histórico no Admin React nesta versão

## Design Considerations

- Manter visual alinhado ao Streamlit atual (Plotly barras, sidebar de filtros existente)
- Deixar claro na UI Histórico que os dados são fotografias diárias (não o operacional “ao vivo”)
- Empty state quando só existir seed-demo ou quando período sem dados

## Technical Considerations

- Volume esperado: centenas de linhas/dia → índices simples bastam
- Reutilizar `processar_entregas` / DataFrame `atrasado` já produzido no job (evitar segundo cálculo divergente)
- `AccessScopeService` obrigatório em qualquer leitura do fato
- Seed demo nunca deve usar `source=job`
- Migrations a partir de **`020`** (sequência atual do repo)

## Success Metrics

- Após o primeiro `report_overdue_daily` bem-sucedido do dia, existe exatamente 1 run para aquele `business_date`
- Admin vê série histórica consolidada; usuário filial não vê dados de outra filial
- Demo ao cliente possível em &lt; 5 minutos com `seed_bi_snapshot_demo.py --days 30 --replace-demo`
- Gráfico 90 dias responde em tempo interativo no volume TMB

## Open Questions

- Em falha ao gravar snapshot: confirmar em code review a política default (log + continua e-mail)
- Situação / tolerância do sidebar: no Histórico, aplicar só dims físicas do fato (filial/cliente/cidade) e ocultar/desabilitar controles que não se aplicam — validar UX na implementação US-005
