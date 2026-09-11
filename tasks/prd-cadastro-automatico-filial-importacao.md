# PRD: Cadastro Automático de Filial na Importação

## Introduction

Hoje a importação de planilha (tela Admin e job `fetch_tmselite_spreadsheet`) **bloqueia o lote** quando a coluna `Sigla Unidade Entrega` traz uma filial inexistente em `prb_users` (perfil `filial`, `enabled`). Isso interrompe a operação diária até cadastro manual (ex.: incidente TMB BARRA MANSA).

Esta feature torna a inexistência de filial um cenário válido: durante a **validação** do lote (`ManualImportService.validate`), o sistema cria automaticamente o usuário/filial com dados básicos (padrão Barra Mansa), registra a ocorrência em **tabela de auditoria dedicada**, e segue a importação sem tratar a ausência como erro. A mesma regra serve aos dois canais porque ambos já passam pelo `ManualImportService`.

Publicação na VPS fica **fora** desta entrega — só após validação local e autorização explícita.

## Goals

- Filial inexistente **não bloqueia** upload/validação/importação (tela e serviço TMS)
- Criação automática **genérica** (sem hardcode de “Barra Mansa”), sem duplicidade no mesmo lote nem em lotes futuros
- Persistência auditável das filiais auto-criadas por lote (sobrevive a refresh do grid)
- UI: coluna **Informação** entre Lote e Ação + modal listando filiais criadas
- Testes locais cobrindo critérios de aceite; sem deploy VPS nesta entrega

## User Stories

### US-001: Migration e repositório de auditoria de filiais auto-criadas
**Description:** As a developer, I need a dedicated audit store for auto-created branches per import batch so the grid/modal can reload after refresh.

**Acceptance Criteria:**
- [ ] Nova migration cria tabela (nome sugerido `prb_import_auto_branches`) com no mínimo: `id`, `batch_id` (FK lote), `user_id` (FK `prb_users`, nullable se útil), `branch` (texto exato da planilha), `login`, `created_on`, `created_by`/`actor`, e constraint que evite duplicar o mesmo `branch` no mesmo `batch_id`
- [ ] Repositório (ou métodos no `ImportRepository`) para inserir e listar por `batch_id`
- [ ] Migration aplicável via fluxo existente (`database/deploy/run_migrations.py` / padrão do projeto)
- [ ] Tests pass

### US-002: Serviço genérico de ensure-filial (padrão Barra Mansa)
**Description:** As a developer, I want a reusable method that finds or creates a filial user from the spreadsheet branch string so import validation stays DRY and idempotent.

**Acceptance Criteria:**
- [ ] Método central (ex.: em `BranchCatalogService` ou helper usado por ele) `ensure_filial_user(branch: str, *, actor: str) -> created: bool` (ou equivalente) que: (1) se `TRIM(branch)` já existe em filiais enabled → não cria; (2) senão cria `prb_users` com `profile=filial`, `branch`=sigla exata, `login`/`code`=slug seguro derivado da sigla, `display_name`/`name`=rótulo legível a partir da sigla, senha padrão do seed de filiais (`tmb123` / mesmo hash path de `seed_filiais_faltantes_import`), `enabled=true`, **sem** `report_emails` nem `login_email`
- [ ] Sem tratamento fixo para “Barra Mansa”; qualquer sigla nova segue a mesma regra
- [ ] Colisão de `login`: tentar sufixo numérico ou falhar de forma controlada (retorno/erro claro) — sem registro incompleto
- [ ] Unit tests cobrindo: já existe / cria nova / mesma branch duas vezes no mesmo processo não duplica
- [ ] Tests pass

### US-003: Validate deixa de rejeitar filial inexistente e auto-cadastra
**Description:** As an admin/operator, I want unknown branches auto-registered during validation so the batch is not blocked by missing filiais.

**Acceptance Criteria:**
- [ ] Em `ManualImportService.validate`, remover o erro “Código da Filial inexistente…”; em vez disso chamar `ensure_filial_user` **uma vez por sigla distinta** do lote (dedupe in-memory + checagem no catálogo)
- [ ] Para cada filial **criada** neste validate, gravar linha na tabela de auditoria (US-001) com `batch_id`, `branch`, `login`, `user_id`, `actor`
- [ ] Filial vazia / obrigatórios atuais continuam gerando erro de validação (comportamento atual para outros campos)
- [ ] Se `ensure_filial_user` falhar (ex.: conflito irrecuperável), a linha/lote registra erro de validação e **bloqueia** importação (decisão 3A)
- [ ] Job TMS e upload pela tela herdam o comportamento (mesmo `validate`)
- [ ] Tests pass

### US-004: API expõe filiais auto-criadas do lote
**Description:** As a frontend developer, I need the import batch payload to include auto-created branches so the Informação column and modal can render.

**Acceptance Criteria:**
- [ ] `GET /api/imports` e `GET /api/imports/{id}` (ou schema `ImportBatchOut`) incluem lista `auto_created_branches` (array de objetos: `branch`, `login`, `user_id`, `created_on` no mínimo)
- [ ] Lista vazia quando não houve criação automática
- [ ] Após refresh/nova consulta, a lista permanece (lida da tabela de auditoria)
- [ ] Tests pass

### US-005: Grid — coluna Informação e modal
**Description:** As an admin, I want an info icon between Lote and Ação when branches were auto-created, opening a modal that lists them and clarifies this is not an import error.

**Acceptance Criteria:**
- [ ] Na tela de Importação de Dados, nova coluna **Informação** entre **Lote** e **Ação**
- [ ] Ícone de informação visível somente quando `auto_created_branches.length > 0`; sem ícone (célula vazia) caso contrário
- [ ] Clique no ícone abre modal com título adequado (“Filial criada automaticamente” / “N filiais foram criadas automaticamente”), lista nome/sigla (+ login/código e data quando disponíveis), lote, e texto deixando claro que **não é erro**
- [ ] Modal lista **todas** as filiais criadas naquele lote
- [ ] Typecheck passes
- [ ] Verify in browser

### US-006: Documentação breve e validação local
**Description:** As an operator, I want a short note in the import docs describing auto-create so support knows the new behavior.

**Acceptance Criteria:**
- [ ] Atualizar `docs/importacao-manual-planilha.md` (seção Validação): filial inexistente → auto-cadastro + auditoria + coluna Informação; falha na criação ainda bloqueia
- [ ] Script/manual smoke local documentado ou coberto por testes: lote com filial nova passa `validated_ok` e grava auditoria; segunda importação da mesma filial não recria
- [ ] Documentation complete

## Functional Requirements

- FR-1: Centralizar a regra em `ManualImportService.validate` (e helper de ensure), cobrindo tela e job TMS sem lógica duplicada
- FR-2: Critério de existência = mesmo do catálogo atual (`profile=filial`, `enabled`, `TRIM(branch)` igual à sigla da planilha)
- FR-3: Criação usa campos mínimos: `login`, `branch`, `display_name`, `name`, `code`, `password_hash` (senha padrão seed), `enabled=true`; sem e-mails
- FR-4: Deduplicar criação por sigla dentro do mesmo lote; não recriar se já existir no catálogo
- FR-5: Persistir criações em tabela dedicada ligada ao `batch_id` (não só memória)
- FR-6: Expor `auto_created_branches` na API de lotes
- FR-7: Grid com coluna Informação + modal; ausência de criações = sem ícone
- FR-8: Falha na criação automática = erro de validação (bloqueia import), com log detalhado
- FR-9: Implementar e testar só em local; **não** publicar VPS nesta PRD

## Non-Goals

- Não alterar cadastro manual em Administração → Usuários (além do que a importação cria)
- Não preencher `report_emails` / `login_email` automaticamente
- Não enviar e-mail ou senha provisória na criação automática
- Não publicar/deploy na VPS nesta entrega
- Não mudar outras regras de validação (cliente obrigatório, duplicidade de entrega, etc.)
- Não criar mapeamento/alias de nomes de filial (ex.: “BARRA DO MANSA” ≠ “BARRA MANSA”)

## Design Considerations

- Reutilizar padrões visuais do Admin React (modal existente tipo `UserModal` / banners de info)
- Coluna Informação estreita, só ícone; tooltip opcional “Filiais criadas automaticamente”
- Mensagem do modal alinhada ao PRD original em `docs/PRD – Cadastro Automático de Filial…md`

## Technical Considerations

- Referência de campos: `database/deploy/seed_filial_barra_mansa.py` e `seed_filiais_faltantes_import.py`
- Validação atual: `BranchCatalogService` + erro em `manual_import_service.py` (~“Código da Filial inexistente”)
- Job TMS já chama o mesmo `ManualImportService` após download — não precisa branch especial no worker
- Slug de login: normalizar sigla (remover `TMB`, acentos, não-alfanuméricos); garantir unicidade
- Senha padrão `tmb123` via `hash_password` (mesmo salt da app) — apenas para o usuário técnico da filial; admin pode trocar depois
- Migration nova numerada após a última existente (ex.: 047+)

## Success Metrics

- Lote com filial nova desconhecida: `validated_ok` + `imported` sem intervenção manual
- Zero duplicatas de `branch` enabled para a mesma sigla após N imports
- Operador vê no grid, após F5, quais filiais aquele lote criou
- Nenhuma regressão: lotes só com filiais já cadastradas comportam-se como hoje (sem ícone Informação)

## Open Questions

- (Resolvido) Persistência: tabela dedicada (4B)
- (Resolvido) Falha na criação: bloqueia como erro de validação (3A)
- (Resolvido) Escopo: backend + UI + testes locais; sem VPS (5A)
- Opcional pós-entrega: política de rotação da senha padrão das filiais auto-criadas
