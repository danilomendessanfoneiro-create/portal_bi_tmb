# PRD: Evolução dashboards, calcConsolidada, clientes e progressão de pedidos

## Introduction

O Portal BI ainda depende, na camada de indicadores, da lógica herdada das macros `calc1.vb` / `calc2.vb` (reproduzida em Python). O cliente consolidou as regras em `calcConsolidada.vb`, que passa a ser a **única** fonte de verdade para o processamento. Em paralelo, o negócio pede filtro multisseleção por Status (sem mudar o comportamento padrão atual), cadastro de Clientes com relatório por CNPJ, ajustes de KPIs no Operacional, e um novo dashboard de **Progressão** baseado em snapshots por upload manual.

Todos os dashboards devem consumir **somente** dados normalizados em PostgreSQL (`prb_*`), sem ler planilha/macros em runtime. Decisões fechadas: (1) default do Status = regra atual de pendentes/atraso, sem pré-filtro por texto de status; (2) snapshot só no **upload manual**; (3) associação cliente↔entrega pelo campo **CNPJ Cliente**; (4) Progressão como **nova aba** no BI Streamlit; (5) análise de impacto (US-001) é entregável obrigatório **antes** de implementar snapshots/Progressão; (6) Pedidos Entregues = `nro_entrega` presente no snapshot/planilha anterior e **ausente** no atual (sumiu do arquivo = entregue); (7) retenção dos snapshots de Progressão = **todo o histórico** (sem purge automático nesta entrega); (8) filtro de transportadora na Progressão **adiado** até existir coluna persistida.

## Goals

- Substituir o processamento de indicadores pela lógica de `calcConsolidada.vb` (paridade validada)
- Eliminar dependência operacional de `calc1.vb` / `calc2.vb`
- Adicionar filtro Status (multiselect) no Operacional e Histórico sem regressão do default
- CRUD de Clientes (Nome, CNPJ, e-mails) + carga inicial a partir de `dados/`
- Relatório automático por Cliente (layout igual ao de filiais; chave CNPJ Cliente)
- Dashboard Progressão com snapshots por upload manual e card Pedidos Entregues
- Ajustar KPIs: remover Valor em Aberto; renomear Entregas em Aberto → Em Atraso
- Garantir origem exclusiva na base normalizada + documentação atualizada
- Entregar análise de impacto (DB/perf/integração) antes de codar Progressão/snapshots

## User Stories

### US-001: Análise de impacto (pré-requisito Progressão)
**Description:** As a tech lead, I need a written impact analysis for snapshots, client reports and processing changes so we can approve scalability and schema before coding Progressão.

**Acceptance Criteria:**
- [x] Documento em `docs/` (ex.: `docs/analise-impacto-progressao-clientes.md`) cobrindo: novas tabelas `prb_*` + audit, índices, retenção, volume de snapshots, impacto em Operacional/Histórico/filtros, relatórios filial vs cliente, compatibilidade upload manual e futura API
- [x] Lista explícita de riscos, impedimentos e recomendações (incluindo se comparação N×N por `nro_entrega` precisa de materialização)
- [x] Confirma decisões: snapshot **somente** em importação manual; chave Progressão = Número da Entrega; match cliente = **CNPJ Cliente**
- [x] Sinalizar no doc que US-012+ (Progressão) só iniciam após este artefato aceito
- [x] Documentation complete

### US-002: Engenharia reversa da calcConsolidada → Python
**Description:** As a developer, I need the consolidated VBA rules mapped and implemented in the Python processing layer so dashboards match Excel on the same file.

**Acceptance Criteria:**
- [x] Documento de mapeamento das regras de `calcConsolidada.vb` (colunas, exclusão `ENTREGUE`, Status Prazo, Retorno Filial, etc.) em `docs/`
- [x] Atualizar `limpeza.py` / serviços de regras (`macro_delivery_rules` ou equivalente) para reproduzir a consolidada
- [x] Remover caminhos de código que dependam de regras exclusivas de `calc1`/`calc2` quando conflitarem com a consolidada
- [x] Teste automatizado (fixture mínima) prova paridade dos indicadores-chave vs expectativa documentada da consolidada
- [x] Tests pass

### US-003: Garantir origem só na base normalizada
**Description:** As a stakeholder, I want every dashboard/report to read only normalized `prb_*` data so Excel macros and raw sheets are never runtime dependencies.

**Acceptance Criteria:**
- [x] Operacional, Histórico, e-mails e jobs não leem CSV/planilha em runtime para KPIs (somente import/persistência)
- [x] Referências operacionais a `calc1.vb`/`calc2.vb` removidas da documentação ativa (podem permanecer como arquivo histórico no repo)
- [x] Checklist curto em `docs/` confirmando consumidores → `prb_deliveries` / lote ativo / snapshots
- [x] Documentation complete

### US-004: Persistir CNPJ Cliente nas entregas
**Description:** As a developer, I need `CNPJ Cliente` stored on each delivery so client reports and filters can match by CNPJ.

**Acceptance Criteria:**
- [x] Migration `prb_deliveries.cnpj_cliente` (texto normalizado dígitos) + audit se o padrão do projeto exigir
- [x] Importação manual e mapper API preenchem `cnpj_cliente` quando disponível (planilha: coluna `CNPJ Cliente`)
- [x] Upsert não perde o campo; listagens BI/API podem expor o valor
- [x] Tests pass

### US-005: Filtro Status multiselect no Operacional
**Description:** As a user, I want a multi-select Status filter on the Operational dashboard so I can analyze subsets without changing the default view.

**Acceptance Criteria:**
- [x] Multiselect de Status no painel de filtros, opções = valores distintos do lote/base filtrável
- [x] **Default:** nenhuma seleção manual de Status → comportamento **idêntico ao atual** (regra de pendentes/atraso vigente; sem pré-marcar status)
- [x] Com 1+ status selecionados: KPIs, gráficos, drill, tabela e detalhe NF recalculam só nesses status
- [x] Sem regressão visual/funcional para quem não usa o filtro
- [x] Verify in browser

### US-006: Filtro Status multiselect no Histórico
**Description:** As a user, I want the same Status multi-select behavior on the History dashboard as on Operational.

**Acceptance Criteria:**
- [x] Mesmo widget/comportamento default e seleção manual do US-005
- [x] Série, detalhe do dia, breakdown e tabela respeitam Status quando selecionado
- [x] Default preserva comportamento atual do Histórico
- [x] Verify in browser

### US-007: Ajustes de cards do Operacional
**Description:** As a manager, I want KPI labels aligned to the business language without changing unrelated metrics.

**Acceptance Criteria:**
- [x] Card **Valor em Aberto** removido do Operacional
- [x] Card **Entregas em Aberto** renomeado para **Em Atraso** (só nomenclatura UI, salvo se US-002 já alterar a regra)
- [x] Layout de KPIs permanece coerente (3 cards ou grade ajustada sem buraco visual)
- [x] Verify in browser

### US-008: Modelo e migrations de Clientes
**Description:** As a developer, I need `prb_clients` (and audit) following portal conventions so CRUD and reports have a durable store.

**Acceptance Criteria:**
- [x] Tabela `prb_clients` com: name, cnpj (único entre enabled), emails (texto), + `created_by/on`, `modified_by/on`, `enabled`
- [x] Tabela `prb_clients_audit` com `created_on_audit`, `action` e espelho dos campos
- [x] Repository + Service (valida CNPJ formato/dígitos, e-mails separados por vírgula individualmente, CNPJ duplicado)
- [x] Tests pass

### US-009: CRUD Admin de Clientes
**Description:** As an admin, I want Administração → Clientes with full CRUD so I can manage report recipients by company.

**Acceptance Criteria:**
- [x] Menu Admin: Administração → Clientes
- [x] Listagem com busca, paginação; create/update; exclusão lógica (`enabled=false`)
- [x] Campos: Nome (obrigatório), CNPJ (obrigatório), E-mails (opcional, múltiplos por vírgula)
- [x] API REST admin-only + UI React alinhada aos CRUDs existentes
- [x] Verify in browser

### US-010: Carga inicial de Clientes a partir de dados/
**Description:** As an admin, I want an initial load of clients from existing spreadsheet data under `dados/` so we do not start empty.

**Acceptance Criteria:**
- [x] Rotina (script/job/comando documentado) lê `dados/` (ex.: `entregas_relatorio.csv`) e upserta clientes distintos por **CNPJ Cliente** + nome Cliente
- [x] E-mails ficam vazios na carga inicial se não existirem na fonte
- [x] Idempotente (reexecutar não duplica CNPJ)
- [x] Documentar comando em `docs/`
- [x] Documentation complete

### US-011: Relatório automático por Cliente (CNPJ)
**Description:** As an operations manager, I want overdue-style emails grouped by Client CNPJ using the same HTML layout as branch reports.

**Acceptance Criteria:**
- [x] Job/fase (ou job irmão reutilizando adapters HTML) agrupa por Cliente via match `prb_clients.cnpj` = entrega.`cnpj_cliente` (normalizado)
- [x] Layout igual ao relatório de filiais; conteúdo só do CNPJ do cliente
- [x] Pula cliente sem CNPJ válido ou sem e-mail cadastrado
- [x] Agendável / disparável de forma documentada (espelhando padrão de filiais onde fizer sentido)
- [x] Tests pass

### US-012: Schema de snapshots de progressão (pós US-001)
**Description:** As a developer, I need dedicated `prb_*` tables for per-upload delivery status snapshots so Progressão can compare loads.

**Acceptance Criteria:**
- [x] Implementar schema recomendado pela US-001 (ex.: run de snapshot + linhas com nro_entrega, status, filial, cliente, cnpj_cliente, batch_id, timestamps) + audit
- [x] Índices para `(snapshot_run_id)`, `(nro_entrega)`, e comparação entre runs
- [x] Não inicia sem US-001 concluída
- [x] Tests pass

### US-013: Capturar snapshot a cada upload manual
**Description:** As a system, I want every successful manual import to persist a progress snapshot of the active dataset at that moment.

**Acceptance Criteria:**
- [x] Ao concluir import manual (`imported`), grava snapshot com data/hora, vínculo ao batch e linhas necessárias
- [x] Sync API **não** gera snapshot nesta entrega (decisão 2A)
- [x] Falha de snapshot não corrompe o import (erro logado / status parcial documentado)
- [x] Tests pass

### US-014: Aba Progressão no BI Streamlit
**Description:** As a user, I want a Progressão tab showing status evolution across uploads with familiar filters and TMB visuals.

**Acceptance Criteria:**
- [x] Nova opção no radio de visão: Operacional | Histórico | Progressão
- [x] Default período diário; usuário pode alterar período
- [x] Gráfico multi-colunas: quantidade por status / evolução entre uploads (a partir do 2º upload)
- [x] Comparação por **Número da Entrega**; filtros: período, cliente, filial, cidade, transportadora (se existir na base), status + filtros já existentes reutilizados quando aplicável
- [x] Verify in browser

### US-015: Card Pedidos Entregues na Progressão
**Description:** As a manager, I want a KPI counting deliveries that left the active spreadsheet between consecutive uploads in the selected period.

**Acceptance Criteria:**
- [x] Card **Pedidos Entregues** no dashboard Progressão
- [x] Conta `nro_entrega` presentes no snapshot anterior e **ausentes** no snapshot atual (sumiu da planilha = entregue), somando pares consecutivos no período filtrado
- [x] Respeita filtros da Progressão
- [x] Verify in browser

### US-016: Documentação final do pacote
**Description:** As a stakeholder, I want architecture, DB, flows and user docs updated for all features in this PRD.

**Acceptance Criteria:**
- [x] Atualizar docs de arquitetura, modelagem, processamento/normalização, clientes, relatórios cliente, progressão/snapshots
- [x] Incluir fluxo/diagrama (Mermaid ou equivalente) upload → snapshot → Progressão
- [x] Manual curto de uso: filtro Status, Clientes, Progressão
- [x] Documentation complete

## Functional Requirements

- FR-1: Processamento de indicadores deve seguir `calcConsolidada.vb`; `calc1`/`calc2` não são fonte de regra em runtime
- FR-2: Dashboards/relatórios leem apenas dados normalizados `prb_*` (lote ativo onde já aplicável)
- FR-3: Filtro Status multiselect no Operacional e Histórico; default sem seleção = comportamento atual (1A)
- FR-4: Com Status selecionados, todos os componentes do dashboard correspondente recalculam só esses status
- FR-5: Remover card Valor em Aberto; renomear Entregas em Aberto → Em Atraso
- FR-6: `prb_clients` (+ audit) com Nome, CNPJ único, e-mails CSV; CRUD Admin
- FR-7: Carga inicial de clientes a partir de `dados/` por CNPJ Cliente
- FR-8: Relatório e-mail por cliente agrupado por CNPJ; match em `cnpj_cliente` da entrega
- FR-9: Snapshot de progressão gerado **somente** em upload manual bem-sucedido
- FR-10: Progressão compara uploads pela chave Número da Entrega; evolução a partir do 2º upload
- FR-11: Card Pedidos Entregues conta `nro_entrega` presentes no snapshot anterior e ausentes no atual (sumiu da planilha), por pares consecutivos no período
- FR-12: Novas tabelas `prb_*` com audit trail padrão do portal
- FR-13: Análise de impacto (US-001) precede implementação de US-012–US-015
- FR-14: Persistência de `cnpj_cliente` nas entregas (import + API quando houver dado)

## Non-Goals

- Snapshot automático na sync API ou job diário (fica para evolução futura)
- Reescrever BI em React / app mobile separado
- Bottom navigation / PWA (já tratados em outro PRD)
- Alterar contrato da API TMS Elite além do mapeamento necessário de CNPJ/status
- Manter dual-run calc1+calc2+consolidada em produção
- Commits durante a implementação (instrução explícita do solicitante: trabalhar na branch atual **sem commit** até pedido explícito)

## Design Considerations

- Reutilizar painel de filtros do BI (`navigation.py`) para Status
- Progressão: terceira aba no radio existente (persistente como Operacional/Histórico)
- CRUD Clientes: mesmo padrão visual de Users/SMTP/Destinatários
- Relatório cliente: reutilizar `worker/adapters/report_html.py` (ou extrair template compartilhado)
- Identidade visual TMB (navy/laranja) nos gráficos Plotly

## Technical Considerations

- Camadas: Repository → Service → API/Controllers; sem regra de negócio no router
- Macro fonte: `calcConsolidada.vb` (exclui linhas `ENTREGUE` no AutoFilter; Status TMS / Status Prazo)
- Planilha `dados/entregas_relatorio.csv` contém `CNPJ Cliente` — mapear no import
- API TMS: garantir campo equivalente a CNPJ Cliente no mapper quando existir no payload
- Ordem sugerida: US-001 → US-002/003/004 → US-005/006/007 → US-008/009/010/011 → (aprovação US-001) US-012/013/014/015 → US-016
- Build/validação após cada story; **não commitar** até o usuário pedir
- Branch: continuar na branch atual de trabalho

## Success Metrics

- Indicadores Operacionais no mesmo arquivo ≈ resultado pós-`calcConsolidada` (checklist documentado)
- Usuário que não toca no Status vê o Operacional/Histórico como hoje
- Admin cadastra cliente e recebe relatório só do seu CNPJ
- Dois uploads manuais sucessivos mostram evolução de status na Progressão
- Zero leitura de VBA/CSV nos dashboards em runtime

## Open Questions

- ~~Lista canônica de status “entrega concluída”?~~ **Fechado:** Pedidos Entregues = `nro_entrega` presente no snapshot/planilha anterior e **ausente** no atual (sumiu do arquivo = entregue). Ver `docs/analise-impacto-progressao-clientes.md` §8.
- ~~Política de retenção de snapshots?~~ **Fechado:** manter **todo o histórico** (sem purge automático nesta entrega).
- ~~Transportadora?~~ **Fechado:** **adiar** filtro até existir coluna persistida.
