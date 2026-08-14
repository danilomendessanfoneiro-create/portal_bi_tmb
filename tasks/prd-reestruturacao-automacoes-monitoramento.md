# PRD: Reestruturação das Automações, Agendamento por Dia e Monitoramento dos Robôs

## Introduction

A tela Administração → Automações hoje agenda jobs por horário (e, em alguns casos, frequência weekly/monthly com um único dia). O cliente precisa de um modelo simples: **horário + dias da semana + ativo/inativo**, sem ver integração via API. Os robôs visíveis (coleta TMS Elite, relatórios de filiais, clientes e gerencial) devem **obrigatoriamente** respeitar esses três critérios antes de executar. Falhas e sucessos precisam ir para um e-mail técnico interno, com SMTP separado do SMTP do cliente, sem aparecer na interface.

“Coleta da Planilha YMS” no briefing original é **erro de digitação**: o robô existente é a **Coleta da planilha TMS Elite** (`fetch_tmselite_spreadsheet`). Não criar um robô YMS.

Implementar na **branch atual**, **sem commits**. Jobs e telas da API permanecem no código e no banco, apenas ocultos e desativados.

## Goals

- Ocultar da UI as automações **Atualização Diária (API Entregas)** e **Migração Inicial (API Entregas)** e o menu **Integração API**, sem apagar código, rotas internas, tabelas ou seeds.
- CRUD de Automações: nome amigável, horário, **sete dias da semana**, ativo/inativo; job_id técnico continua oculto.
- Padrão: seg–sáb marcados, domingo desmarcado; coleta TMS 05:00; relatórios 08:00; **todos os jobs visíveis desativados** até o admin ligar.
- **Todo robô visível só executa se** `enabled = true` **e** o dia atual está nos dias configurados **e** o horário local já atingiu o `local_time` (mesmo contrato `--if-due` de hoje).
- Registrar cada execução em `prb_job_runs` (reutilizar; estender se faltar campo). Tela de histórico **fora desta entrega**.
- Após **cada** robô visível executado (sucesso ou falha), enviar e-mail técnico via SMTP de ambiente, destinatário `jeverson.abreu@gmail.com`.
- Credenciais técnicas só em variáveis de ambiente; nunca na UI nem no código-fonte.

## User Stories

### US-001: Migration de dias da semana e defaults
**Description:** As a developer, I need `run_weekdays` on `prb_job_settings` and seeded defaults so schedules persist Mon–Sat, new times, and disabled jobs.

**Acceptance Criteria:**
- [ ] Migration `041` (próximo número livre) adiciona `run_weekdays` em `prb_job_settings` (array de smallint 0–6, **0=Domingo … 6=Sábado**, alinhado ao `weekday` já existente)
- [ ] Default do array: `{1,2,3,4,5,6}` (segunda a sábado); domingo (0) ausente
- [ ] Audit `prb_job_settings_audit` inclui `run_weekdays` (created_on_audit, action)
- [ ] UPDATE dos jobs visíveis (não só INSERT): `fetch_tmselite_spreadsheet` → 05:00, `enabled=false`, `run_weekdays={1,2,3,4,5,6}`; `report_branch_daily`, `report_client_daily`, `report_managerial` → 08:00, `enabled=false`, mesmos dias
- [ ] `import_deliveries_daily` e `import_deliveries_initial` permanecem no banco com `enabled=false`
- [ ] `frequency` / `weekday` / `day_of_month` **não são dropados** (compatibilidade dos jobs ocultos)
- [ ] Tests pass

### US-002: Scheduler e API respeitam dias + ativo + horário
**Description:** As a system, I want `is_due` and the schedules API to honor weekdays so no visible robot runs on the wrong day or while disabled.

**Acceptance Criteria:**
- [ ] `JobScheduleService.is_due` retorna false se `enabled` é false
- [ ] `is_due` retorna false se o dia civil em `sched.timezone` **não** está em `run_weekdays` (jobs visíveis; se `run_weekdays` vazio → não executa)
- [ ] `is_due` retorna false se `now` ainda não atingiu `local_time` no timezone do job
- [ ] PUT `/api/settings/schedules/{job_id}` aceita `run_weekdays: number[]` (0–6, sem duplicata); rejeita array vazio com mensagem clara
- [ ] GET devolve `run_weekdays` em cada item
- [ ] Coleta TMS, filiais, clientes e gerencial usam **o mesmo** `is_due` (nenhum atalho que ignore dia/ativo)
- [ ] Jobs da API continuam podendo usar `frequency`/`weekday` internos; não aparecem na lista da UI (US-004)
- [ ] Tests pass

### US-003: Robôs visíveis só rodam nos novos critérios
**Description:** As an operator, I want TMS fetch and the three report phases to skip when inactive, on Sunday (default), or before the configured hour so robots obey the new rules.

**Acceptance Criteria:**
- [ ] `fetch_tmselite_spreadsheet --if-due` não executa se desativado, se o dia não está em `run_weekdays`, ou se agora < 05:00 (ou o horário salvo)
- [ ] `report_overdue_daily --if-due` avalia **cada** fase (`report_branch_daily`, `report_client_daily`, `report_managerial`) com o mesmo `is_due`; fase fora dos critérios → `skipped`, não envia e-mail de cliente
- [ ] Domingo com defaults de seed: nenhum dos quatro robôs visíveis dispara via `--if-due`
- [ ] `--force` continua ignorando idempotência, **mas** ainda deve respeitar `enabled` **ou** documentar no código/teste que `--force` só ignora “já rodou hoje”; se `--force` hoje ignora só idempotência, manter isso e garantir que `--if-due` é o caminho do timer
- [ ] Testes cobrem: dia habilitado após horário; dia não habilitado; job desativado; horário ainda não chegou
- [ ] Tests pass

### US-004: Ocultar automações da API na tela
**Description:** As an admin client, I should not see API delivery jobs on Automações so the UI only shows TMS + reports.

**Acceptance Criteria:**
- [ ] GET `/api/settings/schedules` (lista usada pela tela) **não** retorna `import_deliveries_daily`, `import_deliveries_initial` nem alias `import_deliveries`
- [ ] Tela Automações mostra só: Coleta da planilha TMS Elite; Envio Diário de Relatórios das Filiais; Envio Diário de Relatórios dos Clientes; Relatório Gerencial
- [ ] Registros e código dos jobs da API permanecem; systemd/`python -m worker run import_deliveries_daily` ainda existe
- [ ] Os dois jobs da API ficam `enabled=false` após a migration
- [ ] Typecheck passes
- [ ] Verify in browser

### US-005: Ocultar menu Integração API
**Description:** As an admin client, I should not see Configurações → Integração API in the navigation so API setup is not exposed.

**Acceptance Criteria:**
- [ ] Remover o link **Integração API** de `Shell.tsx` e de atalhos em `SettingsPage.tsx` (e qualquer outro nav visível)
- [ ] Rota `/admin/settings/api-integration` e `ApiIntegrationPage` **permanecem** no código (reativação futura)
- [ ] Não apagar `prb_api_settings`, routers nem services
- [ ] Typecheck passes
- [ ] Verify in browser

### US-006: CRUD Automações com dias da semana
**Description:** As an admin, I want checkboxes for the seven weekdays on each visible automation card so I can choose when robots run.

**Acceptance Criteria:**
- [ ] Cada card visível tem seção **Dias de execução** com: Segunda … Sábado, Domingo
- [ ] Padrão visual/seed: seg–sáb marcados, domingo desmarcado
- [ ] Admin pode alterar qualquer combinação (pelo menos um dia); salvar via PUT existente
- [ ] Campos editáveis do card: nome amigável (já existente ou somente leitura se já for `display_name`), horário, dias, ativo/inativo; TMS continua com URL/usuário/senha
- [ ] `job_id` técnico não aparece
- [ ] Typecheck passes
- [ ] Verify in browser

### US-007: Completar registro de execução nos job runs
**Description:** As a developer, I want each robot run stored with timing, status, counts and error step so monitoring emails and a future history screen have data.

**Acceptance Criteria:**
- [ ] Reutilizar `prb_job_runs` (não criar tabela paralela se os campos couberem em `metrics_json` + `started_on`/`finished_on`/`status`/`message`)
- [ ] Se faltar coluna para etapa da falha ou duração, migration `prb_*` + audit com created_by/created_on/modified_by/modified_on/enabled
- [ ] Status persistidos alinhados ao existente: `success` / `failed` (mapear SUCESSO/FALHA no e-mail); `running` já existe (EXECUTANDO); `skipped` não gera e-mail técnico
- [ ] `metrics_json` (ou colunas) inclui quando aplicável: processados, inseridos, atualizados, e-mails enviados, e-mails com erro, etapa da falha
- [ ] Duração derivada de início/fim (guardar `duration_ms` se ainda não houver)
- [ ] Tests pass

### US-008: SMTP técnico e e-mail após cada robô
**Description:** As a technical operator, I want a monitoring email after each visible robot run (success or failure) using env SMTP, not the client SMTP.

**Acceptance Criteria:**
- [ ] Variáveis (nomes estáveis, documentados em `.env.example` **sem senha**): host `smtp.gmail.com`, porta `587`, usuário `jeverson.abreu@gmail.com`, senha só via env, remetente `jeverson.abreu@gmail.com`, nome `jeverson`, destinatário `jeverson.abreu@gmail.com`
- [ ] Nenhuma tela Admin lista esse SMTP, destinatário ou senha; não usar `prb_smtp_settings` nem `prb_email_recipients` para este envio
- [ ] Após **cada** execução real (não `skipped`) de: coleta TMS, filiais, clientes, gerencial — enviar um e-mail
- [ ] Assunto: `Portal BI – Relatório de Execução das Automações – DD/MM/YYYY` (data America/Sao_Paulo)
- [ ] Corpo texto (ou HTML simples) com RESUMO daquele ciclo de **um** robô (planejadas/executadas/sucesso/falha) e DETALHAMENTO (status SUCESSO ou FALHA, início, fim, duração, métricas, erro/etapa se falha); rodapé “Atenciosamente, Portal BI”
- [ ] Execução geral no corpo: `SUCESSO` ou `ATENÇÃO – EXISTEM FALHAS`
- [ ] Falha: destacar automação, horário, etapa, mensagem, quantidade processada antes da falha, se houve envio parcial (quando o job souber)
- [ ] Falha no SMTP técnico **não** desfaz o job de negócio; logar o erro
- [ ] Tests pass (envio mockado)

### US-009: Documentação das automações
**Description:** As an operator, I want docs updated so VPS and local setup match weekday scheduling, hidden API jobs, and technical SMTP.

**Acceptance Criteria:**
- [ ] Atualizar `docs/servico-jobs.md` (e trechos relevantes de `docs/deploy-vps.md` se o timer/env mudar): modelo horário+dias, defaults, jobs visíveis vs ocultos, `--if-due`, monitoramento, env SMTP técnico, fluxo de falha
- [ ] `.env.example` lista as chaves técnicas com valores não-secretos (senha vazia)
- [ ] Documentation complete

## Functional Requirements

- FR-1: Jobs visíveis na UI: `fetch_tmselite_spreadsheet`, `report_branch_daily`, `report_client_daily`, `report_managerial`.
- FR-2: Jobs ocultos na UI, preservados e desativados: `import_deliveries_daily`, `import_deliveries_initial` (e alias `import_deliveries`).
- FR-3: Menu Integração API oculto; rota e backend preservados.
- FR-4: `run_weekdays` com 0=Domingo … 6=Sábado; default 1–6.
- FR-5: Coleta TMS horário padrão 05:00; os três relatórios 08:00; todos `enabled=false` após migration.
- FR-6: **Regra obrigatória dos robôs:** executar somente se ativo **e** dia ∈ `run_weekdays` **e** horário local ≥ `local_time` no timezone do job (`America/Sao_Paulo` padrão).
- FR-7: Admin altera nome amigável (se o card já permite), horário, dias e ativo; TMS: URL, usuário, senha cifrada (já existente).
- FR-8: Cada execução visível grava run (início, fim, duração, status, métricas, erro/etapa).
- FR-9: E-mail de monitoramento após cada robô visível executado (sucesso ou falha), SMTP 100% env, To/From `jeverson.abreu@gmail.com`.
- FR-10: `skipped` (fora da janela, desativado, dia errado, idempotência) não dispara e-mail técnico.
- FR-11: Não expor senha SMTP técnica, e-mail técnico nem jobs da API na interface do cliente.
- FR-12: Timers systemd continuam chamando `--if-due`; jobs da API no mesmo unit não disparam se `enabled=false`.

## Non-Goals

- Não criar robô YMS.
- Não apagar jobs, tabelas, páginas ou rotas da API.
- Não implementar tela de consulta do histórico nesta entrega (só persistência).
- Não usar o SMTP cadastrado pelo cliente para o e-mail técnico.
- Não colocar senha SMTP no repositório, PRD versionado com segredo, ou UI.
- Não commits (instrução desta entrega).
- Não alterar o conteúdo dos relatórios de atraso enviados a filiais/clientes/gerencial além do gate de agendamento e do gancho de monitoramento.
- Não secret manager externo (só variáveis de ambiente).

## Design Considerations

- Reutilizar cards de `frontend/src/pages/SchedulePage.tsx`; adicionar grupo de checkboxes “Dias de execução”.
- Ocultar nav em `Shell.tsx` e `SettingsPage.tsx`; não remover `ApiIntegrationPage`.
- Lista GET de schedules: filtro no backend (fonte da verdade), não só no React.
- E-mail técnico: texto alinhado ao exemplo do briefing, mas **um robô por mensagem** (decisão 3A).

## Technical Considerations

- Coluna nova `run_weekdays` em vez de sobrecarregar `weekday` (um único dia da frequência weekly).
- `JobScheduleService.is_due` é o único gate para `--if-due` nos quatro robôs visíveis.
- `prb_job_runs` + `worker/idempotency.py` já registram success/failed/running/skipped; estender métricas.
- SMTP técnico: módulo pequeno (ex. `app/services/tech_smtp.py`) lendo `os.getenv`; senha nunca logada.
- Host técnico informado: `smtp.gmail.com:587`, STARTTLS, user/from `jeverson.abreu@gmail.com`, from name `jeverson`.
- Testes de regressão em `tests/test_worker_report.py` e testes da coleta TMS devem passar a incluir dia da semana.
- Impacto: scheduler, jobs, banco, tela Automações, logs, e-mails de negócio (não disparam se skipped). Migration deve ser idempotente (`IF NOT EXISTS` / `ON CONFLICT`).

## Success Metrics

- Domingo (default): `--if-due` não dispara nenhum robô visível.
- Sábado 08:01 com jobs ativos: as três fases de relatório entram na janela; coleta só se ≥ 05:00.
- Admin não vê Integração API nem jobs de API na tela Automações.
- Cada execução real gera uma linha em `prb_job_runs` e um e-mail técnico (mock em teste).
- Cliente SMTP permanece exclusivo dos relatórios de atraso.

## Open Questions

- Confirmar nomes exatos das env vars no `.env` da VPS no deploy (sugestão: `TECH_SMTP_HOST`, `TECH_SMTP_PORT`, `TECH_SMTP_USER`, `TECH_SMTP_PASSWORD`, `TECH_SMTP_FROM`, `TECH_SMTP_FROM_NAME`, `TECH_SMTP_TO`).
- `--force` no CLI: nesta entrega mantém o comportamento atual (ignora só idempotência do dia), não os dias da semana — timers de produção usam `--if-due`.
