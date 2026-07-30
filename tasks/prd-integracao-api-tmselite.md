# PRD: Integração API de Entregas (TMS Elite)

## Introduction

O Portal BI ainda depende de `dados/entregas_relatorio.csv`. Esta feature implementa a integração com a API TMS Elite (Bearer Token), configuração administrativa parametrizável, importação paginada para PostgreSQL (`prb_*`), automações de carga inicial e atualização diária, e logs de execução — de forma que o BI passe a consumir a base local com resultado o mais próximo possível do CSV atual (o CSV deixa de ser fonte operacional).

Referência estrutural de desenvolvimento: `model.json` (dados de teste). Exemplo de consumo (valores reais só via admin, nunca hardcoded):

```bash
curl --location 'https://app.tmselite.com/api/v1/entregas/relatorios/geral?dataCadastroInicio=2026-07-01&dataCadastroFim=2026-07-27&currentPage=1&pageSize=500' \
  --header 'Authorization: Bearer <token>'
```

**Decisões fechadas nesta versão:**
- Chave de integração: `remessa.numero` (persistido como identificador único da entrega).
- Sync diário: filtro por `dataCadastro` (janela do dia / parâmetros do job); filtros extras (status, data entrega etc.) ficam preparados na config/client para evolução sem redesign.
- Carga inicial: dias configuráveis na configuração da API (default **90**).
- Token: Bearer estático no CRUD (sem renovação automática nesta etapa).
- Migrations: continuar a sequência do projeto a partir de **`014`** (não reutilizar números do rascunho).
- Resultado: BI lê Postgres; CSV **não** é mais utilizado como fonte.

## Goals

- Camada `app/integrations/tmselite/` desacoplada (client, mapper, service, models, exceptions)
- CRUD admin **Configurações → Integração API** (`prb_api_settings` + audit), com padrão único e token criptografado
- Upsert paginado em tabelas `prb_*` alinhadas ao pipeline do BI (`limpeza` / COLUNAS_UTEIS)
- Automações: migração inicial (default 03:00) e atualização diária (default 07:00) via `prb_job_settings`
- Logs de integração (`prb_integration_logs` + audit) com métricas de páginas/registros/erros
- Substituir a leitura do CSV no BI pela base importada

## User Stories

### US-001: Camada de integração TMS Elite
**Description:** As a developer, I want a dedicated integration package for TMS Elite so that API auth, pagination, timeouts and mapping stay isolated from UI and domain services.

**Acceptance Criteria:**
- [ ] Pacote `app/integrations/tmselite/` com `client.py`, `mapper.py`, `service.py`, `models.py`, `exceptions.py`
- [ ] Client usa Bearer Token, URL base + endpoint, timeout e `pageSize` vindos da config padrão (não hardcoded)
- [ ] Paginação: percorre páginas até esgotar (`pager` quando existir; senão fim quando página retornar menos que `pageSize` ou vazia)
- [ ] Erros HTTP / timeout / JSON inválido viram exceptions tipadas + logs
- [ ] Mapper converte item `results[]` → modelo interno; chave única = `str(remessa.numero)`
- [ ] Mapper produz campos equivalentes ao CSV/BI (`nota_fiscal`, `cliente`, `filial`, datas, valores, motorista, etc.) usando `model.json` como referência; lacunas documentadas em notas/logs
- [ ] Nenhum router/controller Streamlit chama HTTP da API diretamente
- [ ] Tests pass

### US-002: CRUD Configuração Integração API
**Description:** As an administrador, I want to configure API base URL, endpoint, token, timeout and page size in the admin so that environments can change without code changes.

**Acceptance Criteria:**
- [ ] Migrations `014_create_prb_api_settings.sql` + `015_create_prb_api_settings_audit.sql` (campos de auditoria padrão + `enabled`)
- [ ] Campos: nome, base_url, endpoint, token (criptografado), timeout_seconds, page_size, initial_load_days (default 90), is_default, enabled
- [ ] Service: apenas uma config `is_default=true` ativa; token nunca retornado em claro na listagem (máscara); update de token só se informado
- [ ] API FastAPI + tela React em Configurações → **Integração API** (CRUD)
- [ ] Job/service de importação resolve sempre a config padrão ativa
- [ ] Typecheck passes
- [ ] Verify in browser

### US-003: Persistência de entregas e upsert
**Description:** As an operador, I want deliveries upserted into PostgreSQL by remessa number so that re-runs update without duplicates and the dataset mirrors the CSV shape for the BI.

**Acceptance Criteria:**
- [ ] Migrations `016+` criando tabela flat de entregas (ex.: `prb_deliveries`) + `_audit`, com `created_by/on`, `modified_by/on`, `enabled`, metadados `synced_at`, `source`, opcional `raw_json`
- [ ] Unique constraint em `remessa_numero` (ou coluna equivalente mapeada de `remessa.numero`)
- [ ] Colunas cobrem o conjunto necessário ao BI (`limpeza.COLUNAS_UTEIS` / indicadores); mapping documentado no código do mapper
- [ ] Repository upsert (insert novos / update existentes) sem duplicar pela chave
- [ ] Service de importação: consulta API → todas as páginas → mapper → upsert; métricas inserted/updated/errors
- [ ] Tests pass

### US-004: Logs de integração
**Description:** As an operador, I want each sync run logged with timing and counts so that failures are diagnosable.

**Acceptance Criteria:**
- [ ] Migrations para `prb_integration_logs` (+ audit se padrão do projeto exigir réplica)
- [ ] Campos: started_on, finished_on, duration_ms (ou derivado), pages_processed, rows_inserted, rows_updated, error_count, error_message, status, filtro datas, job/automation id, actor
- [ ] Toda execução (sucesso/falha/parcial) grava log; falha de API não deixa run “fantasma” sem status final
- [ ] Tests pass

### US-005: Jobs worker — carga inicial e diária
**Description:** As an operador, I want worker jobs for initial load and daily cadastro sync so that imports run on schedule without hardcoded times.

**Acceptance Criteria:**
- [ ] Substituir/estender stub `import_deliveries` (ou jobs `import_deliveries_initial` / `import_deliveries_daily`) no registry CLI
- [ ] Carga inicial: janela `hoje - initial_load_days` → `hoje` (config padrão), filtrando `dataCadastroInicio/Fim`
- [ ] Atualização diária: janela por `dataCadastro` do dia de negócio (America/Sao_Paulo); parâmetros futuros (status, data entrega) previstos na assinatura/config sem implementação obrigatória agora
- [ ] Flags `--dry-run` (não grava upsert / ou rollback documentado), `--force`, `--date`, `--if-due`
- [ ] Idempotência alinhada a `prb_job_runs` por automação + business_date quando aplicável
- [ ] Seeds em `prb_job_settings`: automação carga inicial 03:00; diária 07:00; `display_name` amigáveis; `frequency=daily`
- [ ] Tests pass

### US-006: Automações na UI admin
**Description:** As an administrador, I want to enable/disable and set local times for the two import automations on the Automações screen so that schedules stay configurable.

**Acceptance Criteria:**
- [ ] Tela Automações lista as duas novas automações com nomes funcionais (sem expor job_id técnico)
- [ ] Edição de horário + ativo; sem horários fixos no código do worker além dos seeds
- [ ] `--if-due` respeita enabled + local_time + timezone
- [ ] Typecheck passes
- [ ] Verify in browser

### US-007: BI lê Postgres em vez do CSV
**Description:** As a usuário do BI, I want dashboards and report jobs to use imported deliveries so that CSV is no longer required for day-to-day operation.

**Acceptance Criteria:**
- [ ] Pipeline de dados (`limpeza` / load do dashboard / job de relatório) lê de `prb_deliveries` (ou view/service), produzindo o mesmo contrato de colunas derivadas (`atrasado`, `vence_hoje`, `prazo_considerado`, etc.)
- [ ] CSV deixa de ser fonte operacional (fallback opcional só se tabela vazia + log de aviso, ou falha clara — documentar a escolha no código/docs)
- [ ] Relatório HTML / worker de atrasos continua funcionando sobre a nova fonte
- [ ] `docs/integracao-api-tmselite.md` e `docs/servico-jobs.md` / README atualizados (chave `remessa.numero`, fim do CSV, migrations `014+`)
- [ ] Tests pass

## Functional Requirements

- FR-1: Integração HTTP somente via `app/integrations/tmselite`
- FR-2: Auth Bearer com token da config padrão; URL base, endpoint, timeout, page_size e initial_load_days parametrizáveis
- FR-3: Paginação completa até esgotar resultados
- FR-4: Upsert por `remessa.numero` sem duplicidades
- FR-5: Mapper baseado em `model.json`, visando paridade com colunas do BI/CSV
- FR-6: CRUD admin Integração API com auditoria `prb_*` / `_audit`
- FR-7: Logs em `prb_integration_logs` com métricas de execução
- FR-8: Duas automações (carga inicial 03:00 seed; diária 07:00 seed) em Automações
- FR-9: Sync diário filtra por `dataCadastro`; client/config preparados para filtros adicionais futuros
- FR-10: BI e jobs de relatório usam a base importada; CSV não é fonte operacional
- FR-11: Migrations incrementais a partir de `014`
- FR-12: Workers reutilizam registry CLI existente (`python -m worker …`)

## Non-Goals

- Renovação automática de token / OAuth
- Implementação completa de filtros extras (status, data entrega) além do gancho/parametrização preparatória
- Manter CSV como fonte paralela de produção
- Alterar a API do fornecedor TMS Elite
- Commit automático (trabalho na branch atual; commits só se o usuário pedir)

## Design Considerations

- Reutilizar padrão visual das telas SMTP / Automações no React admin
- Token mascarado na UI; campo senha só no create/update
- Automações: mesmos cards de “Automações”, sem expor IDs técnicos

## Technical Considerations

- Reutilizar `secret_box` (como SMTP) para criptografar o Bearer token
- Reutilizar `prb_job_settings` / `JobScheduleService` / `--if-due` já existentes
- `model.json` pode divergir do tenant TMB real: documentar lacunas (ex.: `filial`/sigla, `motivo_atraso`, `peso_taxado`) e mapear o melhor equivalente
- Chave: `remessa.numero` (não `pedidos.numero`, salvo se mapper precisar de ambos para exibição)
- Stack: Python, FastAPI, React, PostgreSQL, worker CLI
- Branch atual; sem commits no loop de implementação salvo pedido explícito

## Success Metrics

- Importação completa de uma janela sem duplicar remessas
- BI exibe indicadores sem depender do CSV
- Admin altera URL/token/horários sem deploy de código
- Falhas de API aparecem em `prb_integration_logs` com status e mensagem

## Open Questions

- Campo definitivo de **filial/sigla TMB** no payload real (sample usa nomes genéricos em `unidades.*`) — validar com tenant TMB
- Semântica exata de data de entrega no JSON (`recebedor.data` vs campo dedicado)
- Quais query params extras a API aceita (status, data entrega) quando o fornecedor documentar — gancho já previsto
- Comportamento se `remessa.numero` vier nulo em algum registro (rejeitar linha + contar erro vs skip)
