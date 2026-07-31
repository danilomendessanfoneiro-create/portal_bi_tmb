---
title: Drill-down do Dashboard Histórico (espelho do dia)
created: 2026-07-31
status: done
tags: [bi, historico, streamlit]
related: ["tasks/prd-bi-historico-snapshots.md", ".atlas/plans/2026-07-30-bi-historico-snapshots.md"]
---

# Plano: Drill-down do Dashboard Histórico (espelho do dia)

## Objetivo

Permitir que, no **Dashboard Histórico**, o usuário clique em qualquer dia do gráfico de barras e abra um dashboard detalhado — **espelho das informações daquele dia** — com nível semelhante ao **Dashboard Gerencial/Operacional** (KPIs + registros), restrito ao snapshot da data selecionada. Pronto = clique no dia mostra indicadores e lista de entregas em atraso daquela fotografia, com o mesmo controle de acesso (admin × filial).

## Contexto

### Estado atual
- Aba **Histórico** (`app/controllers/history_controller.py`): só agregados diários (`BiSnapshotService.aggregate_series`) + gráfico de barras.
- Snapshots já existem no grain **entrega atrasada** (`prb_bi_snapshot_overdue`), com dims suficientes (filial, cliente, cidade, NF, prazo, dias_atraso, valor, etc.).
- Não há ainda API/repo para listar fatos de **um** `business_date` (só agregação por dia e opções de filtro).
- Drill por clique já é padrão no Operacional (`st.plotly_chart` + `on_select` / session_state).

### Viabilidade
**Viável e de baixo risco de modelo de dados** — a persistência já guarda o espelho linha a linha. O trabalho é majoritariamente **consulta + UI Streamlit**, sem nova migration obrigatória.

| Aspecto | Avaliação |
|---------|-----------|
| Dados | OK — fatos por dia já gravados no snapshot |
| Escopo de acesso | Reaproveitar `AccessScopeService` (filial só vê a própria) |
| Paridade “Gerencial” | Parcial: snapshot = só **atrasados** do dia; Operacional atual também tem “vence hoje / em dia”. Espelho fiel do Histórico = KPIs/lista de atrasos da foto |
| Performance | Aceitável para um dia; índices `(business_date)` / `(filial, business_date)` já previstos |
| UX | Clique na barra → painel/página “Dia DD/MM/AAAA” com voltar ao gráfico |

### Fora de escopo (nesta fase)
- Reconstruir “vence hoje / em dia” histórico (não está no snapshot atual).
- Backfill de dias sem snapshot.
- Alterar o job de captura ou o conteúdo dos e-mails.

## Abordagem

1. **Query** `list_overdue_for_day(business_date, filtros, filiais)` no repository/service.
2. **UI**: no Histórico, `plotly_chart` com seleção; ao clicar um dia, renderizar seção “Detalhe do dia” (KPIs: qtde, valor total, média dias atraso; barras por filial/cliente; tabela detalhada) lendo só o snapshot daquele dia + filtros ativos.
3. Alternativa descartada: reprocessar `prb_deliveries` “como se fosse o dia” — **não** reproduz a foto histórica (dados operacionais mudam).

Referência de produto (pedido):

> Avaliar a viabilidade de implementar no Dashboard Histórico clique em qualquer dia do gráfico para visualizar um novo dashboard contendo o espelho das informações daquele dia, com detalhamento semelhante ao Dashboard Gerencial, indicadores e registros exclusivos da data selecionada.

## Passos
- [x] Spec curta com cliente: confirmar se “Gerencial” = só atrasos da foto ou espelho completo Operacional (implica ampliar snapshot) — **decisão: só atrasados (1A)**
- [x] PRD formal em `tasks/prd-drilldown-dashboard-historico.md` (decisões 1A/2A/3A/4C)
- [x] Adicionar `list_overdue_for_day` no `BiSnapshotRepository` + método no `BiSnapshotService`
- [x] Testes: filtro filial/cliente/cidade/busca; filial não vaza outra branch
- [x] Histórico: capturar clique no gráfico (`business_date` em session_state) + fallback selectbox
- [x] Renderizar painel “Detalhe do dia” (KPIs + breakdown + drill + tabela) com botão limpar/voltar
- [x] Documentar em `docs/`
## Riscos & Mitigações
- Expectativa de paridade total com Operacional (incl. não-atrasados) → snapshot atual não tem; alinhar escopo ou estender captura depois.
- Clique Plotly inconsistente no Streamlit → fallback: `selectbox`/`date_input` “Dia para detalhar” ao lado do gráfico.
- Volume alto num dia → paginar tabela / `st.dataframe` com altura limitada.

## Questões em aberto
- (fechadas) Tabela: `dias_atraso` desc como Operacional; `status_prazo` sim (já no fato); título UI = **Detalhe do dia**.
