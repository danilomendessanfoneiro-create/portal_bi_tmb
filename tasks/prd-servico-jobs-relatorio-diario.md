# PRD: Serviço de Jobs — Relatório Diário de Atrasos

## Introduction

O Portal BI TMB já possui dashboards (Streamlit), administração (React + FastAPI) e cadastros de SMTP / destinatários de e-mail. Falta um **serviço independente em Python** que, de forma agendada, gere e envie relatórios operacionais sem depender da interface web.

Esta entrega implementa o **worker de jobs** com o **ReportJob diário consolidado** (entregas em atraso → CSV único → um e-mail para os destinatários diários), reutilizando as configurações já existentes. A **importação automática via API de terceiros** permanece apenas como contrato/stub arquitetural — **não será implementada nesta PRD**.

Fonte de dados nesta fase: `dados/entregas_relatorio.csv` processado via `limpeza.py` (mesma lógica de atraso do BI).

## Goals

- Disponibilizar um worker CLI no monorepo (`worker/`) desacoplado de Streamlit/React
- Gerar relatório CSV consolidado de entregas em atraso (todas as filiais)
- Enviar **um único e-mail** com o CSV anexado aos destinatários com “relatório diário” ativos, usando SMTP padrão
- Evitar reenvio duplicado no mesmo dia de negócio (`prb_job_runs`)
- Permitir horário de disparo **configurável** (padrão 07:00 America/Sao_Paulo) via Configurações no admin
- Rodar localmente para testes agora; na VPS via systemd após deploy
- Preparar extensão futura (`import_deliveries` stub + registry de jobs)

## User Stories

### US-001: Esqueleto do worker e registry de jobs
**Description:** Como desenvolvedor, quero um pacote `worker/` com CLI e registro de jobs para executar rotinas batch sem acoplar à UI.

**Acceptance Criteria:**
- [ ] Pacote `worker/` com CLI: `python -m worker list` e `python -m worker run <job_id> [--force] [--date YYYY-MM-DD] [--dry-run] [--if-due]`
- [ ] Registry permite registrar jobs por `job_id` estável
- [ ] Job `import_deliveries` existe como **stub** (no-op documentado; não chama API nem grava entregas)
- [ ] Worker reutiliza `app.config.settings` / venv do projeto (sem segundo requirements obrigatório)
- [ ] Documentation complete

### US-002: Persistência de execução e idempotência
**Description:** Como operador, quero que o job diário não reenvie o mesmo relatório no mesmo dia sem necessidade, com histórico auditável de execuções.

**Acceptance Criteria:**
- [ ] Migration incremental `prb_job_runs` (padrão `prb_*`: created_by/on, modified_by/on, enabled) + índices por `(job_id, business_date, status)`
- [ ] Antes de enviar e-mail, se já existir run `success` para `(report_overdue_daily, business_date)` sem `--force`, o job encerra sem reenvio
- [ ] Cada execução grava status (`running` / `success` / `failed` / `skipped`), início/fim, mensagem de erro (se houver) e métricas básicas (linhas, destinatários)
- [ ] Auditoria da tabela de runs conforme padrão do projeto (tabela `*_audit` + trigger) **ou** justificativa documentada se runs forem append-only sem update de negócio
- [ ] Tests pass

### US-003: Geração do CSV consolidado de atrasos
**Description:** Como área operacional, quero um arquivo CSV com todas as entregas em atraso de todas as filiais para acompanhamento diário.

**Acceptance Criteria:**
- [ ] Job `report_overdue_daily` lê `dados/entregas_relatorio.csv` via a mesma regra de negócio de atraso usada no BI (`limpeza` / critérios alinhados a `AccessScopeService` + prazo)
- [ ] Gera **um** CSV consolidado (todas as filiais) em `storage/reports/YYYY-MM-DD/atrasos_consolidado.csv`
- [ ] Colunas mínimas: código da entrega, cliente, filial, data prevista, data de referência, dias em atraso, status, transportadora (se existir), demais campos úteis já disponíveis no dataset processado
- [ ] `--dry-run` gera o CSV (ou reporta contagem) **sem** enviar e-mail
- [ ] Tests pass

### US-004: Envio de e-mail único com anexo
**Description:** Como administrador, quero que o relatório consolidado seja enviado automaticamente por e-mail aos destinatários cadastrados para relatório diário.

**Acceptance Criteria:**
- [ ] Utiliza SMTP marcado como padrão (`SmtpSettingsService` / `MailDispatchService`)
- [ ] Destinatários: ativos com `receive_daily = true` (`EmailRecipientService`)
- [ ] Envia **um** e-mail (não um por filial) com o CSV consolidado em anexo
- [ ] Assunto/corpo incluem data de referência e totais (ex.: quantidade de atrasos / filiais distintas)
- [ ] Falha de SMTP marca o run como `failed` e registra erro; não marca `success`
- [ ] Senha SMTP permanece descriptografada só em memória no worker (`secret_box`)
- [ ] Tests pass

### US-005: Horário configurável nas Configurações
**Description:** Como administrador, quero definir o horário do disparo diário (padrão 07:00) para testar com flexibilidade e ajustar em produção sem redeploy de código.

**Acceptance Criteria:**
- [ ] Persistência de configuração de agendamento (ex.: `prb_job_settings` ou equivalente `prb_*`) com: job_id, horário local (HH:MM), timezone (default `America/Sao_Paulo`), enabled, campos de auditoria padrão
- [ ] Seed/default: `report_overdue_daily` às **07:00** America/Sao_Paulo, enabled=true
- [ ] API admin (FastAPI) para ler/atualizar essa configuração (somente admin)
- [ ] Tela no Admin React em Configurações (ex.: “Agendamento de relatórios”) permitindo alterar horário e ativo/inativo
- [ ] CLI `run … --if-due` só executa o envio se, na timezone configurada, o horário atual já atingiu o HH:MM do dia **e** ainda não houve `success` na `business_date`
- [ ] Execução sem `--if-due` (padrão do CLI manual) **ignora** a janela horária (para testes locais)
- [ ] Verify in browser

### US-006: Deploy local e artefatos VPS
**Description:** Como operador, quero rodar o job localmente agora e ter units systemd prontas para a VPS após o deploy.

**Acceptance Criteria:**
- [ ] Documentação em `docs/servico-jobs.md` (ou atualização) com comandos locais de teste
- [ ] Units systemd: service + timer que invocam `python -m worker run report_overdue_daily --if-due` em intervalo adequado (ex.: a cada 15 min) para respeitar o horário configurável
- [ ] `.gitignore` cobre `storage/reports/` gerados (ou política clara do que versionar)
- [ ] Documentation complete

## Functional Requirements

- FR-1: O worker deve ser um processo/CLI independente; não deve exigir Streamlit ou o frontend no ar
- FR-2: O job `report_overdue_daily` deve produzir um CSV consolidado de atrasos e enviar um único e-mail aos destinatários diários
- FR-3: A fonte de dados nesta fase é o CSV do repositório processado por `limpeza.py`
- FR-4: SMTP e destinatários devem vir exclusivamente das tabelas/services já existentes (`prb_smtp_settings`, `prb_email_recipients`)
- FR-5: Idempotência por `business_date` (dia de referência do relatório) via `prb_job_runs`, contornável com `--force`
- FR-6: Horário padrão 07:00 America/Sao_Paulo, editável no admin; disparo automático usa `--if-due`
- FR-7: O job `import_deliveries` existe apenas como stub documentado (sem API, sem escrita de entregas)
- FR-8: Logs de execução devem ir para stdout (e opcionalmente arquivo sob `logs/jobs/`) com job_id, status e duração

## Non-Goals

- Integração com a API de terceiros de entregas
- Rotina real de importação / carga em `prb_deliveries`
- Migrar o BI Streamlit para ler do Postgres nesta PRD
- Um e-mail por filial ou ZIP com vários CSVs
- Celery, Redis, filas distribuídas
- UI para “disparar relatório agora” (pode ser fase futura; CLI cobre testes)
- Relatórios semanal/mensal (flags de destinatário existem, jobs ficam para depois)

## Design Considerations

- Admin: manter identidade TMB; tela de agendamento simples (horário + toggle ativo) dentro de Configurações
- E-mail: texto claro em pt-BR; evitar HTML complexo nesta fase
- CSV: encoding UTF-8 com BOM se necessário para Excel

## Technical Considerations

- Reutilizar: `limpeza.processar_planilha`, `MailDispatchService`, `SmtpSettingsService`, `EmailRecipientService`, `secret_box`, padrão migrations em `database/migrations/`
- Novo: pacote `worker/`, migrations de `prb_job_runs` (+ settings de schedule), adapters de mailer (smtplib), pages/API de agendamento
- VPS já usa systemd para API/BI — mesmo padrão para o timer do worker
- Porta/API do admin já existente; não criar serviço HTTP só para o worker
- Decisões fechadas desta especificação: escopo 1B; fonte 2A (CSV); e-mail consolidado único; horário flexível via configuração; execução local + VPS pós-deploy

## Success Metrics

- Execução local `python -m worker run report_overdue_daily --dry-run` gera CSV sem erro
- Execução com SMTP/destinatários de teste envia um e-mail com anexo
- Segunda execução no mesmo `business_date` sem `--force` resulta em `skipped` (sem novo e-mail)
- Admin consegue alterar o horário e o `--if-due` respeita a nova configuração
- Stub `import_deliveries` listável no `worker list` sem efeitos colaterais

## Open Questions

- [x] Escopo: esqueleto + ReportJob completo — **1B**
- [x] Fonte: CSV atual — **2A**
- [x] E-mail: consolidado único para destinatários diários — **3D (fechado)**
- [x] Agendamento: 07:00 default + configurável no admin — **4D**
- [x] Runtime: CLI local agora; VPS após deploy — **5D**
- [x] Formato do anexo consolidado: **um CSV** (não ZIP / não multi-anexo por filial)

*Nenhuma open question pendente. Aguardando sinal para iniciar implementação.*
