# PRD: Upload de Planilha para Atualização Manual dos Dados

## Introduction

O Portal BI atualiza entregas principalmente via integração API (TMS Elite) e, em fallback operacional, via migração CSV (`dados/entregas_relatorio.csv` → `prb_deliveries`). Administradores ainda precisam de um caminho **manual e guiado** na interface para atualizar a base quando a API estiver indisponível ou quando a planilha operacional for a fonte do dia.

Este PRD define um módulo **Administração → Importação de Dados** (somente admin) com fluxo em duas etapas: (1) upload + validação completa **sem** gravar em `prb_deliveries`; (2) confirmação e importação efetiva com upsert, progresso, histórico e disparo em background dos jobs de relatório já existentes (filiais + gerencial).

## Goals

- Permitir que administradores importem planilha no layout operacional (CSV atual e Excel `.xlsx`/`.xls`) pela UI do Admin React
- Garantir validação completa em staging antes de qualquer alteração em `prb_deliveries`
- Bloquear importação se houver qualquer inconsistência (incluindo filial inexistente no cadastro)
- Aplicar upsert por `remessa_numero` / `nro_entrega`, reutilizando o pipeline de mapeamento/tratamento já usado no projeto
- Registrar histórico auditável de cada lote de importação
- Após sucesso, disparar automaticamente em background os jobs de relatório existentes (sem bloquear a UI)
- Documentar fluxo, tabelas, validações e disparo de jobs

## User Stories

### US-001: Migrations de lote, staging e auditoria
**Description:** As a developer, I need `prb_*` tables for import batches, staging rows and history so validation can run without touching `prb_deliveries`.

**Acceptance Criteria:**
- [ ] Criar migrations incrementais para `prb_import_batches`, `prb_import_batch_items` (staging) e `prb_import_logs` (ou campos de histórico no batch), com `created_by`/`created_on`/`modified_by`/`modified_on`/`enabled` onde aplicável
- [ ] Criar tabelas de auditoria e triggers no padrão do projeto (`prb_*_audit`)
- [ ] Batch guarda metadados do arquivo (nome, tamanho, hash opcional), status (`uploaded` | `validating` | `validated_ok` | `validated_error` | `importing` | `imported` | `failed`), contadores e tempos
- [ ] Staging referencia `batch_id` e preserva número da linha da planilha para mensagens de erro
- [ ] Tests pass

### US-002: Catálogo de filiais para validação de existência
**Description:** As an admin, I want import to reject unknown branch codes and tell me to register the branch so data stays consistent with access control.

**Acceptance Criteria:**
- [ ] Fonte de verdade: filiais distintas em `prb_users` com `profile = 'filial'`, `enabled = true` e `branch` não nulo/vazio
- [ ] Serviço de validação consulta essa fonte; filial vazia ou inexistente gera erro de linha e **bloqueia** o lote
- [ ] Mensagem de erro sugere cadastrar a filial via **Administração → Usuários** (usuário perfil filial com o campo Filial)
- [ ] Tests pass

### US-003: API de upload e criação de batch em staging
**Description:** As an admin, I want to upload one spreadsheet file so the system can stage rows for validation.

**Acceptance Criteria:**
- [ ] Endpoint autenticado admin-only para upload multipart (um arquivo por request)
- [ ] Aceitar `.csv`, `.xlsx`, `.xls`; rejeitar outros tipos com 400 e mensagem clara
- [ ] Rejeitar arquivo vazio/corrompido; para Excel, validar existência da aba/planilha esperada (primeira aba ou aba documentada)
- [ ] Persistir arquivo em storage do projeto (path configurável) e criar `prb_import_batches` + popular staging **sem** escrever em `prb_deliveries`
- [ ] Reutilizar ao máximo o mapeamento de colunas do CSV atual (`limpeza` / `CsvDeliveryImportService` / `COLUNAS_UTEIS`), convertendo Excel para o mesmo schema interno
- [ ] Tests pass

### US-004: Serviço de validação completa do lote
**Description:** As an admin, I want a full validation pass on staged data so I can fix the spreadsheet before any production update.

**Acceptance Criteria:**
- [ ] Endpoint/serviço `validate` que lê apenas staging do batch; **não** altera `prb_deliveries`
- [ ] Validar estrutura: colunas obrigatórias do layout `dados/`, colunas desconhecidas/duplicadas, tipos
- [ ] Validar dados: datas, números, obrigatórios vazios, duplicidade de chave (`nro_entrega`/`remessa_numero`) **dentro** da planilha, filial inexistente (US-002)
- [ ] Cada erro registra linha + mensagem específica (ex.: `Linha 35: Pedido 000123 possui data no formato inválido.`)
- [ ] Atualiza contadores do batch (total / válidos / erros) e status `validated_ok` ou `validated_error`
- [ ] Tests pass

### US-005: Tela Admin — Upload, validação e resultado
**Description:** As an admin, I want a Importação de Dados screen with drag-and-drop and clear validation results so I can operate the two-step flow.

**Acceptance Criteria:**
- [ ] Menu **Administração → Importação de Dados** visível só para `admin` (filial não vê)
- [ ] UI: drag-and-drop, botão selecionar arquivo, metadados (nome, tamanho, data de alteração), botões Validar Planilha e Importar Dados
- [ ] Importar Dados permanece desabilitado até `validated_ok` (zero erros)
- [ ] Após validação, exibir totais (registros, válidos, erros) e lista detalhada de erros
- [ ] Identidade visual alinhada ao Admin React existente
- [ ] Typecheck passes
- [ ] Verify in browser

### US-006: Importação efetiva com upsert e transação
**Description:** As an admin, I want confirmed import to upsert deliveries by remessa/nro_entrega using existing business rules so the BI base stays consistent with API/CSV pipelines.

**Acceptance Criteria:**
- [ ] Endpoint `import` só aceita batch em `validated_ok`; caso contrário 409/400
- [ ] Lê staging → mapeia para `DeliveryRecord` / upsert em `prb_deliveries` por `remessa_numero` (mesmo contrato do import CSV/API)
- [ ] Reaplica regras de limpeza/macros já usadas no pipeline (`limpeza` / `macro_delivery_rules` conforme aplicável na gravação)
- [ ] Toda a carga do batch em **uma transação**; erro ⇒ rollback completo e status `failed` com log
- [ ] Atualiza contadores inseridos/atualizados e status `imported`
- [ ] Tests pass

### US-007: Progresso da importação na UI
**Description:** As an admin, I want progress feedback during import so large files are operable without guessing.

**Acceptance Criteria:**
- [ ] Durante importação, UI mostra barra de progresso com percentual, processados e restantes (polling ou streaming conforme padrão do projeto)
- [ ] Ao concluir, exibir resumo (processados, atualizados, inseridos, tempo total)
- [ ] Typecheck passes
- [ ] Verify in browser

### US-008: Histórico de importações
**Description:** As an admin, I want a searchable history grid of past imports for audit and support.

**Acceptance Criteria:**
- [ ] Grid na mesma tela com: data/hora, usuário, arquivo, total, inseridos, atualizados, erros, tempo, status
- [ ] Filtros por data, usuário, arquivo e status
- [ ] Dados vindos das tabelas `prb_import_*` (não inventar histórico só em memória)
- [ ] Typecheck passes
- [ ] Verify in browser

### US-009: Disparo automático dos jobs de relatório após importação
**Description:** As an admin, I want filial and gerencial report jobs to run automatically in the background after a successful manual import so stakeholders get updated emails without waiting for the schedule window.

**Acceptance Criteria:**
- [ ] Após `imported` com sucesso, enfileirar/disparar em background a execução dos jobs existentes de relatório (fase filiais + gerencial), **reutilizando** o worker/job atual (não reimplementar geração/envio na tela)
- [ ] Disparo **não** bloqueia a resposta da API de importação; falha no disparo é logada e refletida no histórico/log do batch sem desfazer o upsert já commitado
- [ ] Usar modo que ignore janela `--if-due` para este trigger manual pós-import (ex.: `--force` / flag equivalente já suportada pelo CLI), documentado no código
- [ ] Justificativa da Alternativa 1 (jobs existentes) registrada em docs da feature
- [ ] Tests pass

### US-010: Documentação do módulo de importação manual
**Description:** As a maintainer, I want project docs updated so operators and developers understand the manual import flow.

**Acceptance Criteria:**
- [ ] Atualizar docs do repositório com: fluxo upload→staging→validação→import, tabelas, regras de validação, upsert, disparo dos jobs, modelo de planilha suportado (CSV + Excel)
- [ ] Incluir fluxograma (Mermaid) do processo
- [ ] Documentation complete

## Functional Requirements

- FR-1: O sistema deve expor a tela **Importação de Dados** apenas para perfil `admin`
- FR-2: O sistema deve aceitar um único arquivo por upload nos formatos `.csv`, `.xlsx` e `.xls`, no layout compatível com `dados/entregas_relatorio.csv` / `COLUNAS_UTEIS`, com limites de **20 MB** e **100.000 linhas** (rejeitar acima disso na validação inicial)
- FR-2b: Arquivos importados em `storage/imports/` **podem ser retidos** (sem purge automático obrigatório nesta entrega; path e metadados no batch para auditoria)
- FR-3: O upload deve gravar metadados + staging; **não** pode escrever em `prb_deliveries` antes da confirmação
- FR-4: A validação deve cobrir estrutura e dados, com erros endereçados por linha e mensagem explícita
- FR-5: Filial obrigatória e existente em `prb_users` (perfil `filial`, enabled); se inexistente, bloquear o lote e sugerir cadastro em Administração → Usuários
- FR-6: Qualquer erro de validação mantém `Importar Dados` desabilitado (política all-or-nothing)
- FR-7: A importação efetiva deve fazer upsert por `remessa_numero`/`nro_entrega` em transação única
- FR-8: A UI deve mostrar progresso e resumo final da importação
- FR-9: O sistema deve persistir histórico consultável de importações
- FR-10: Após importação bem-sucedida, o sistema deve disparar em background os jobs de relatório já existentes (filiais + gerencial), sem bloquear a UI
- FR-11: Camadas API → Service → Repository; reutilizar mapeamento/upsert existentes sempre que possível

## Non-Goals

- Não substituir a integração API TMS Elite como fluxo principal contínuo
- Não implementar geração semanal/mensal de relatório gerencial (permanece fora de escopo; gerencial diário via job existente)
- Não permitir importação parcial de linhas válidas quando houver erros no lote
- Não expor a funcionalidade a usuários `filial`
- Não abrir upload público sem autenticação admin
- Não redesenhar o BI Streamlit; a feature é no Admin React + API FastAPI
- Não exigir REPLACE total da base (diferente do migrate CSV `--replace`); o modo é **upsert**

## Design Considerations

- Seguir identidade visual do Admin React (cards, botões, tipografia já usados em Usuários/Configurações)
- Drag-and-drop + seletor de arquivo; estados claros: sem arquivo → validando → erros → pronto para importar → importando → concluído
- Histórico na parte inferior da mesma página
- Mensagens de erro em português, com número da linha

## Technical Considerations

- Stack: FastAPI + services/repositories + PostgreSQL `prb_*`; frontend em `frontend/src/pages`
- Reutilizar: `limpeza.COLUNAS_UTEIS`, `CsvDeliveryImportService` / `DeliveryRepository.upsert`, `macro_delivery_rules` na medida em que o pipeline de gravação já as aplica
- Excel: converter para o mesmo DataFrame/schema interno do CSV (biblioteca já alinhada ao projeto ou dependência leve documentada)
- Storage de arquivos: sob `storage/imports/` (ou path em settings); **retenção permitida** (sem job de purge nesta entrega)
- Limites de upload: **20 MB** e **100.000 linhas**
- Filiais válidas: distinct `branch` de `prb_users` (`profile='filial'`, `enabled=true`)
- Progresso: atualizar contadores no batch para polling da UI (simples e alinhado ao stack atual)
- Pós-import: subprocess/async task chamando `python -m worker run report_overdue_daily --force` (ou API interna equivalente), sem duplicar HTML/SMTP
- Performance: staging em bulk insert; validação em batch; evitar N+1

## Success Metrics

- Admin consegue validar e importar planilha operacional sem acesso SSH/SQL
- Zero escrita em `prb_deliveries` quando a validação falha
- Filiais desconhecidas nunca entram na base via este fluxo
- Após import OK, jobs de relatório são disparados sem travar a tela
- Histórico permite auditar quem importou o quê e com qual resultado

## Open Questions

- (Resolvido) Filiais: validar contra `prb_users` (perfil filial enabled)
- (Resolvido) Limites: 20 MB / 100k linhas
- (Resolvido) Arquivos em `storage/imports/` podem ser retidos; purge automático fora desta entrega
- Staging (`prb_import_batch_items`) após `imported`: manter para auditoria nesta entrega (purge opcional futuro)
