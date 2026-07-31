# PRD: Drill-down do Dashboard Histórico — Espelho do Dia

## Introduction

O **Dashboard Histórico** hoje mostra apenas a evolução agregada (barras: dia × quantidade de atrasos). O usuário não consegue investigar **por que** um dia específico teve aquele volume nem ver o detalhe das entregas daquela fotografia.

Esta feature adiciona um **drill-down**: ao clicar em qualquer dia do gráfico (com fallback por seletor), o sistema abre um **espelho do dia** — dashboard com KPIs, breakdown e registros **somente das entregas em atraso** capturadas no snapshot daquela `business_date`, no mesmo espírito do Dashboard Gerencial/Operacional, respeitando o escopo admin × filial.

**Decisões fechadas (com o cliente):**
- Escopo do espelho = **apenas atrasados** da foto (`prb_bi_snapshot_overdue`). Não inclui “vence hoje / em dia”.
- Abertura = **clique na barra** + **fallback selectbox** “Dia para detalhar”.
- No detalhe (admin): **drill** por filial/cliente como no Operacional (gráficos clicáveis + tabela filtrada).
- KPIs mínimos = qtde em atraso + valor total + média de dias em atraso **+** breakdown por filial (admin) / cliente (perfil filial).
- Título da seção UI = **“Detalhe do dia”** (não “Espelho do dia”).
- Tabela ordenada por `dias_atraso` **desc** (igual Operacional).
- Coluna `status_prazo` na tabela: **sim** (já existe no fato `prb_bi_snapshot_overdue`).
- Sem migration nova: reutilizar o grain já persistido.
- Não reler `prb_deliveries` “como se fosse o dia” (isso não reproduz a foto histórica).

Referências: `.atlas/plans/2026-07-31-drilldown-dashboard-historico.md`, `tasks/prd-bi-historico-snapshots.md`.

## Goals

- Permitir investigar um dia histórico com o mesmo nível de detalhe útil do Gerencial (atrasos da foto)
- Abrir o espelho por clique no gráfico, com fallback se a seleção Plotly falhar
- Reutilizar filtros ativos do Histórico e `AccessScopeService` (filial nunca vê outra branch)
- Expor KPIs + breakdown dimensional + tabela de registros do dia selecionado
- Manter imutabilidade do snapshot (somente leitura)

## User Stories

### US-001: Consulta de fatos do snapshot por dia
**Description:** As a developer, I want `list_overdue_for_day` (repository + service) so that the UI can load the overdue rows of a single `business_date` with the same filters and access scope as the historical series.

**Acceptance Criteria:**
- [ ] `BiSnapshotRepository` lista linhas de `prb_bi_snapshot_overdue` para um `business_date` (enabled), com filtros opcionais filial / cliente / cidade / busca (NF ou cliente)
- [ ] `BiSnapshotService.list_overdue_for_day(...)` retorna `DataFrame` (ou lista tipada) pronto para o Streamlit
- [ ] Admin pode filtrar qualquer filial; perfil filial é sempre restrito a `viewer.branch` (nunca vazamento)
- [ ] Não lê `prb_deliveries`
- [ ] Unit tests: filtros, dia sem dados → vazio, escopo filial
- [ ] Tests pass

### US-002: Seleção do dia no gráfico Histórico
**Description:** As a usuário do BI, I want to click a day on the historical bar chart (or pick it from a fallback selector) so that the system knows which snapshot day to mirror.

**Acceptance Criteria:**
- [ ] `st.plotly_chart` do Histórico captura seleção de barra e grava `business_date` em `st.session_state`
- [ ] Fallback: selectbox (ou equivalente) listando os dias presentes na série agregada filtrada — “Dia para detalhar”
- [ ] Botão/ação “Limpar detalhe do dia” remove a seleção e volta ao modo só série
- [ ] Dia inválido / fora da série / sem snapshot → mensagem clara, sem crash
- [ ] Verify in browser

### US-003: Painel Detalhe do Dia — KPIs e breakdown
**Description:** As a usuário do BI, I want KPIs and a dimensional breakdown for the selected day so that I can compare volume, value and concentration (filial or cliente) at a glance.

**Acceptance Criteria:**
- [ ] Com dia selecionado, exibe seção **“Detalhe do dia DD/MM/AAAA”**
- [ ] KPIs: quantidade em atraso; valor total em atraso; média de dias em atraso
- [ ] Breakdown em barras: **filial** se admin; **cliente** se perfil filial (respeitando escopo)
- [ ] Dados vêm só do snapshot do dia + filtros do painel Histórico já aplicados
- [ ] Verify in browser

### US-004: Drill dimensional e tabela de registros
**Description:** As an admin (or filial user), I want to click the breakdown chart and see the filtered table of deliveries for that day so that I can investigate individual NFs like on the Operacional dashboard.

**Acceptance Criteria:**
- [ ] Clique no gráfico de breakdown grava drill (filial ou cliente) em session_state e filtra KPIs auxiliares / tabela
- [ ] Tabela lista registros do snapshot do dia (NF, cliente, filial, cidade, prazo, dias atraso, valor, status, status_prazo, motorista — campos disponíveis no fato), ordenada por `dias_atraso` desc (como Operacional)
- [ ] Ação para limpar o drill dimensional sem sair do dia
- [ ] Empty state quando o dia/filtros não retornam linhas
- [ ] Verify in browser

### US-005: Documentação
**Description:** As a developer, I want a short doc update so that the team knows how the day mirror works and its limits vs Operacional.

**Acceptance Criteria:**
- [ ] Atualizar doc do Histórico / contrato (ex. `docs/` ou seção em doc existente) descrevendo: clique → **Detalhe do dia**; só atrasados da foto; não reconstrói “vence hoje/em dia”
- [ ] Referenciar este PRD e o plano `.atlas/plans/2026-07-31-drilldown-dashboard-historico.md`
- [ ] Documentation complete

## Functional Requirements

- FR-1: O sistema deve carregar o espelho exclusivamente de `prb_bi_snapshot_overdue` (e metadados do run, se útil), nunca recalculando atraso a partir de `prb_deliveries` para o dia histórico.
- FR-2: Ao selecionar um dia (clique ou fallback), o sistema deve exibir KPIs: `count(*)`, `sum(valor_total)`, `avg(dias_atraso)` das linhas filtradas daquele dia.
- FR-3: O sistema deve exibir breakdown por filial (admin) ou por cliente (filial), com drill por clique filtrando a tabela.
- FR-4: Filtros do painel Histórico (busca, filial, cliente, cidade, janela) devem continuar aplicando-se ao espelho do dia.
- FR-5: `AccessScopeService` deve restringir perfil filial à própria branch em todas as consultas do espelho.
- FR-6: Deve existir forma de limpar a seleção do dia e o drill dimensional.
- FR-7: Se não houver snapshot/linhas para o dia, mostrar empty state informativo (não erro genérico).

## Non-Goals

- Não ampliar o snapshot para incluir “vence hoje” / “em dia” / entregas não atrasadas
- Não alterar o job de captura nem o conteúdo dos e-mails
- Não fazer backfill de dias sem snapshot
- Não criar migration nova (salvo descoberta bloqueante documentada)
- Não implementar a visão espelho fora do Streamlit (Admin React fora de escopo)
- Não exportar PDF/Excel do espelho nesta fase

## Design Considerations

- Reutilizar `kpi_card`, padrões de `plotly` + `on_select` / session_state do Operacional (`dashboard_controller.py`)
- Manter a série agregada visível acima (ou com botão voltar) para não perder o contexto da evolução
- Título da seção: **Detalhe do dia DD/MM/YYYY**
- Tabela com `st.dataframe` / column_config; ordenação `dias_atraso` desc; incluir `status_prazo`; altura limitada se volume alto

## Technical Considerations

- Estender `BiSnapshotRepository` / `BiSnapshotService`; ponto de UI: `history_controller.py`
- Índices existentes em `(business_date)` e `(filial, business_date)` devem bastar
- Clique Plotly no Streamlit pode ser inconsistente → fallback selectbox obrigatório (decisão 2A)
- Testes em `tests/test_bi_snapshot.py` (ou novo módulo) cobrindo listagem e escopo

## Success Metrics

- Usuário chega do gráfico ao NF individual do dia em ≤ 3 interações (clique dia → drill opcional → linha na tabela)
- Zero vazamento de filial em testes de escopo
- Sem regressão na série agregada do Histórico quando nenhum dia está selecionado

## Open Questions

- Nenhuma no momento (decisões de ordenação, `status_prazo` e título da UI fechadas em 2026-07-31).
