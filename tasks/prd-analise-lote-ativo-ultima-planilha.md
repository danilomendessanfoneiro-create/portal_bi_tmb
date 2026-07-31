# PRD: Análise BI somente sobre o último lote de dados

## Introduction

Hoje o Dashboard Operacional, os e-mails de atraso e o snapshot do Histórico leem **todas** as entregas habilitadas em `prb_deliveries` (acúmulo de imports manuais + sincronizações da API). Isso diverge do fluxo Excel das macros (`calc1`/`calc2`), que analisa **apenas a planilha aberta** — um recorte do dia.

Esta feature muda a fonte de análise para o **lote ativo**: por padrão a **última planilha importada com sucesso**; se ainda não houver importação manual, a **última sincronização bem-sucedida da API** passa a ser o lote. O histórico no banco **permanece** (sem replace/apagar cargas antigas); apenas a **leitura** para indicadores, relatórios e snapshots filtra o lote ativo. Admin e usuários de filial usam a mesma base, com o filtro de filial já existente.

## Goals

- Fazer com que todo o pipeline que hoje usa `processar_entregas` / `list_for_bi` considere somente o **lote ativo**
- Definir lote ativo = último `prb_import_batches` com `status = imported` (planilha); fallback = última sincronização API bem-sucedida
- Manter histórico de entregas e de lotes no banco (sem delete em massa das cargas anteriores)
- Preservar o controle de acesso por filial (admin vê tudo do lote; filial vê só a sua)
- Aproximar a contagem de atrasos do BI à da macro Excel no **mesmo arquivo** (meta de paridade)
- Exibir no BI/Admin qual lote está ativo (arquivo, data, origem planilha|api)

## User Stories

### US-001: Marcar entregas com o lote de origem
**Description:** As a developer, I need each delivery row linked to its import batch or API sync run so the BI can filter the active dataset without deleting history.

**Acceptance Criteria:**
- [x] Migration: coluna em `prb_deliveries` para origem do lote (ex.: `dataset_batch_id` nullable FK lógica ao import batch, e/ou `dataset_sync_id` / `dataset_source` documentado)
- [x] Importação manual (`source = manual_upload`) grava o `batch_id` do lote em todas as linhas upsertadas daquele import
- [x] Job de importação API grava identificador da execução (ex.: `prb_job_runs.id` ou equivalente) nas linhas sincronizadas naquela run
- [x] Upsert não apaga entregas de lotes anteriores; apenas atualiza/insere e associa ao lote corrente da operação
- [x] Tests pass

### US-002: Resolver e persistir o “lote ativo”
**Description:** As a developer, I need a single rule to resolve which dataset is active for analysis so all consumers stay consistent.

**Acceptance Criteria:**
- [x] Serviço (ex.: `ActiveDatasetService`) resolve: (1) último batch `imported` habilitado; senão (2) última sync API success; senão (3) conjunto vazio com motivo documentado
- [x] Resolução é a mesma para BI, worker de e-mails e captura de snapshot
- [x] Opcional recomendado: tabela/settings `prb_active_dataset` (ou equivalente) atualizada ao concluir import manual ou job API, evitando recalcular em toda request — se cachear, invalidar nos mesmos pontos
- [x] Tests pass

### US-003: Filtrar `list_for_bi` / `processar_entregas` pelo lote ativo
**Description:** As a user, I want Operational KPIs and delay rules to run only on the active dataset so numbers match the last spreadsheet (or last API sync).

**Acceptance Criteria:**
- [x] `DeliveryRepository.list_for_bi` (ou wrapper) retorna somente entregas `enabled` do lote ativo
- [x] `limpeza.processar_entregas` consome essa lista filtrada; regras de macro (`cliente_conta` / atraso) permanecem
- [x] Sem lote resolvível: DataFrame vazio (ou erro controlado) com mensagem clara no BI — não voltar silenciosamente ao “tudo acumulado”
- [x] Tests pass

### US-004: E-mails e snapshot usam o mesmo lote ativo
**Description:** As an operations manager, I want overdue emails and history snapshots based on the same dataset as the Operational dashboard.

**Acceptance Criteria:**
- [x] `report_overdue_daily` (fases filiais + gerencial) carrega atrasados via `processar_entregas` já filtrado pelo lote ativo
- [x] Snapshot pós-import e snapshot no job de relatório usam o mesmo filtro
- [x] Documentar que `--force` reenvia e-mails do lote ativo atual, não reabre lotes antigos
- [x] Tests pass

### US-005: Indicação do lote ativo na UI (BI + Admin)
**Description:** As an admin or branch user, I want to see which file/sync is driving the analysis so I trust the KPIs.

**Acceptance Criteria:**
- [x] BI Operacional mostra faixa/info: origem (`planilha` | `api`), nome do arquivo ou id da sync, data/hora, contagem de linhas do lote (quando disponível)
- [x] Admin → Importação de Dados indica qual batch é o lote ativo atual (destaque no histórico ou badge)
- [x] Usuário filial vê a mesma indicação de lote (sem dados de outras filiais nas tabelas)
- [x] Verify in browser

### US-006: Paridade com macro no mesmo arquivo + documentação
**Description:** As a stakeholder, I want documented proof that overdue count on the last uploaded sheet is close to Excel macros on that same file.

**Acceptance Criteria:**
- [x] Checklist em `docs/` (ex.: `docs/paridade-lote-ativo-macros.md`): importar arquivo X → BI atrasados ≈ count `01_ATRASO` pós-macro no mesmo X (mesma data de referência)
- [x] Teste automatizado (fixture mínima ou CSV de amostra) prova que `processar_entregas` após “ativar lote” não inclui remessas só de lotes anteriores
- [x] Atualizar `docs/importacao-manual-planilha.md` e `docs/analise-prazo-considerado.md` com a regra do lote ativo
- [x] Documentation complete

## Functional Requirements

- FR-1: O sistema deve associar cada entrega gravada por importação manual ao `batch_id` correspondente
- FR-2: O sistema deve associar cada entrega gravada/atualizada por job de API ao identificador da sincronização correspondente
- FR-3: O **lote ativo** deve ser: último batch manual `imported`; se inexistente, última sincronização API com sucesso
- FR-4: `list_for_bi` / `processar_entregas` devem retornar somente entregas do lote ativo (`enabled = true`)
- FR-5: Dashboard Operacional, e-mails (`report_overdue_daily`) e snapshots do Histórico devem consumir exclusivamente o lote ativo
- FR-6: Filtro de acesso por filial permanece depois do filtro de lote (admin = todas as filiais do lote; perfil filial = subset)
- FR-7: Entregas de lotes anteriores permanecem no banco para auditoria; não entram no cálculo enquanto não forem o lote ativo
- FR-8: A UI do BI e a tela de Importação devem exibir qual lote está ativo (origem, rótulo, timestamp)
- FR-9: Reimportar a mesma ou nova planilha com sucesso deve tornar esse batch o novo lote ativo imediatamente após `status = imported`
- FR-10: Disparo manual de e-mails usa o lote ativo no momento do disparo

## Non-Goals

- Não apagar / truncate de `prb_deliveries` a cada upload (replace destrutivo)
- Não misturar automaticamente “última planilha ∪ última API” no mesmo cálculo
- Não permitir ao usuário escolher lote antigo na UI nesta versão (sem seletor histórico de dataset)
- Não alterar a regra de atraso em si (`Dt. Prazo Atual` + exclusão das 5 contas); só o universo de linhas
- Não reprocessar snapshots históricos já gravados sob a regra antiga
- Não mudar layout das macros Excel VBA

## Design Considerations

- BI: banner compacto acima dos KPIs (origem + nome do arquivo / “Sync API #id” + data)
- Admin Importação: badge “Lote ativo” na linha do batch correspondente
- Reutilizar estilos existentes do Streamlit/Admin; evitar cards decorativos no hero

## Technical Considerations

- Ponto único de leitura: preferir alterar `DeliveryRepository.list_for_bi` + `ActiveDatasetService` para não espalhar filtros
- Import manual hoje faz upsert por `remessa_numero`: uma remessa reimportada muda de lote; remessas **só** do lote antigo somem da análise (desejado para paridade com planilha)
- Atenção: se a planilha for subset e o upsert atualizar só essas remessas, remessas antigas de outros clientes continuariam no banco mas fora do lote ativo — correto para 2B
- API fallback (3C): definir claramente o que é “uma sync” (um `prb_job_runs` success de `import_deliveries_*`) e garantir que todas as linhas tocadas na run recebam o mesmo `dataset_sync_id`
- Performance: índice em `(dataset_batch_id)` / `(dataset_sync_id)` + `enabled`
- Compatível com exclusão `cliente_conta` / aliases NINFA já corrigidos

## Success Metrics

- No mesmo arquivo CSV/XLSX e mesma data de referência, atrasados do BI ≈ atrasados `01_ATRASO` após macros (meta: diferença justificada documentada; idealmente 0 após exclusões alinhadas)
- Após novo import, KPIs mudam para refletir só esse arquivo (sem inflar com lotes anteriores)
- Zero regressão de ACL: usuário filial não vê outras filiais
- E-mails e Operacional batem no mesmo total de atrasados do lote ativo (mesmo instante)

## Open Questions

- Remessas presentes só em lotes antigos e ausentes na última planilha: confirmado que **ficam fora** da análise (sim, pela FR-7) — stakeholders ok?
- Quando a API rodar **depois** de um import manual, a API deve **assumir** o lote ativo (substituindo a planilha) ou a planilha permanece ativa até o próximo upload manual?
- Precisamos de toggle admin “congelar lote ativo” para não sobrescrever com sync API automática?
- Tolerância aceitável na meta 5A (ex.: ±0, ±5, ±2%) quando houver diferença de fuso/arredondamento de data?
