# PRD: Ajustes no Envio de Relatórios por E-mail e Parametrização das Automações

## Introduction

O Portal BI já envia um relatório diário consolidado (CSV anexo) aos destinatários administrativos. Esta evolução separa dois fluxos de envio, individualiza o relatório por filial, remove anexos em favor de HTML no corpo do e-mail e torna a parametrização das automações independente e legível na tela de agendamentos.

**Decisão de arquitetura (job único):** é possível manter **um único job executor** (ex.: `report_overdue_daily`) que orquestra as duas fases (filiais + gerencial). A parametrização fica em **duas automações** independentes em `prb_job_settings` (horário/frequência distintos). Com `--if-due`, o job executa apenas a(s) fase(s) cujo horário/frequência estiver devido. Semanal/mensal do gerencial: nesta etapa só persiste e expõe a configuração; a geração desses relatórios fica fora de escopo (log explícito se disparado).

## Goals

- Cadastrar um ou mais e-mails por usuário de perfil filial (separados por `;`)
- Enviar a cada filial apenas os dados da própria filial, em HTML no corpo do e-mail (sem anexo)
- Enviar aos destinatários administrativos o consolidado diário em HTML (sem anexo), com assunto/corpo usando o **nome do destinatário**
- Manter periodicidade diária das filiais e parametrização independente do gerencial (diário / semanal / mensal)
- Renomear a UX de “Jobs” para “Automações” e ocultar nomes técnicos
- Preservar arquitetura em camadas, `prb_*`, auditoria e segregação de dados por filial

## User Stories

### US-001: Campo de e-mails no cadastro de usuários filial
**Description:** As an administrador, I want to cadastrar um ou mais e-mails no usuário de perfil filial so that cada filial tenha destinatários próprios do relatório diário.

**Acceptance Criteria:**
- [ ] Coluna `report_emails` (TEXT, nullable) em `prb_users` + migration incremental `prb_*` com auditoria (`prb_users_audit` atualizada se necessário)
- [ ] API e formulário de Usuários (React admin) permitem informar e-mails separados por `;`
- [ ] Validação no Service: trim por endereço, formato de e-mail individual, sem duplicatas na mesma filial/usuário; gravação bloqueada com mensagem indicando o endereço inválido
- [ ] Campo visível/obrigatório apenas quando perfil = `filial` (ou gravado vazio para outros perfis)
- [ ] Tests pass

### US-002: Dois fluxos independentes no job único
**Description:** As an operador, I want o envio automático separado entre filiais e gerencial so that cada público receba o conteúdo correto sem misturar dados.

**Acceptance Criteria:**
- [ ] Job único orquestra **Fase A (filiais)** e **Fase B (gerencial)**; cada fase respeita sua automação/`--if-due`
- [ ] Fase A: para cada usuário ativo perfil `filial` com `branch` e `report_emails`, filtra dados só daquela filial e envia 1 e-mail por endereço (já existente no mailer)
- [ ] Filial sem e-mails: log de aviso e **pula** (não falha o job inteiro)
- [ ] Fase B: destinatários de `prb_email_recipients` (flags diárias já existentes); conteúdo consolidado de todas as filiais
- [ ] Segregação: nenhuma filial recebe dados de outra
- [ ] Logs detalham sucesso/falha por filial e por destinatário gerencial
- [ ] Tests pass

### US-003: Corpo HTML sem anexos (filial e gerencial diário)
**Description:** As a destinatário, I want receber o relatório no corpo do e-mail em HTML so that eu possa ler no Outlook/Gmail sem abrir anexo.

**Acceptance Criteria:**
- [ ] Removido envio de anexo CSV nos fluxos diários desta feature
- [ ] Assunto filial: `Relatório de Entregas - [Nome da Filial]`
- [ ] Assunto gerencial: `Relatório de Entregas - [Nome do Destinatário]` (nome do cadastro de destinatários; fallback e-mail)
- [ ] Corpo segue o texto aprovado (Bom dia… 16h00… Notas em atraso / que vencem hoje… Atenciosamente), trocando `[Nome da Filial]` pelo nome da filial (fase A) ou pelo **nome do destinatário** (fase B)
- [ ] Tabelas HTML com colunas: Nota Fiscal, Cliente, Cidade, Valor (R$ pt-BR), Dias em atraso
- [ ] Seção vazia exibe: `Nenhuma nota fiscal nesta situação.`
- [ ] HTML simples compatível com Outlook e Gmail (sem CSS complexo / sem dependência de assets externos)
- [ ] Artefato local CSV em `storage/reports/` permanece opcional só para auditoria/debug se já existir; **não** vai no e-mail
- [ ] Tests pass

### US-004: Tela de Schedules como Automações
**Description:** As an administrador, I want ver “Automações” com nomes amigáveis so that eu configure horários sem ver IDs técnicos de job.

**Acceptance Criteria:**
- [ ] Na UI admin, rótulos “Jobs” substituídos por “Automações” (menu, títulos, labels)
- [ ] Nome técnico (`job_id`) oculto na interface; exibido apenas label funcional (ex.: “Envio Diário de Relatórios das Filiais”, “Relatório Gerencial”)
- [ ] Lista/edição mostra as duas automações com campos funcionais
- [ ] Typecheck passes
- [ ] Verify in browser

### US-005: Parametrização independente das automações
**Description:** As an administrador, I want configurar horário/frequência do gerencial separado das filiais so that cada fluxo tenha sua própria agenda.

**Acceptance Criteria:**
- [ ] Migration estende `prb_job_settings` (ou equivalente `prb_*` + audit) com: `display_name`, `frequency` (`daily`|`weekly`|`monthly`), `weekday` (nullable, 0=Domingo…6=Sábado), `day_of_month` (nullable, 1–31), mantendo `local_time`, `timezone`, `enabled` e auditoria padrão
- [ ] Seed/atualização: Automação 1 — relatório das filiais, `daily`, horário atual (ex. 07:00), enabled
- [ ] Seed/atualização: Automação 2 — relatório gerencial, `daily` inicial, horário configurável; UI permite `weekly` (dia da semana + horário) e `monthly` (dia 1–31 + horário)
- [ ] Validações no Service: weekly exige weekday; monthly exige day_of_month 1–31; daily ignora weekday/day_of_month
- [ ] `--if-due` do job único avalia cada automação independentemente e executa só a fase correspondente
- [ ] Frequências weekly/monthly do gerencial: **apenas parametrização**; se due, registrar log “geração semanal/mensal não implementada nesta etapa” e **não** falhar a fase de filiais
- [ ] Typecheck passes
- [ ] Verify in browser

### US-006: Documentação e critérios operacionais
**Description:** As a desenvolvedor, I want documentação atualizada do serviço de jobs so that a operação saiba como rodar e o que mudou no e-mail.

**Acceptance Criteria:**
- [ ] `docs/servico-jobs.md` atualizado: dois fluxos, HTML sem anexo, e-mails em usuário filial, automações independentes, comportamento weekly/monthly (só config)
- [ ] Comandos CLI de dry-run / force / if-due documentados para o job único
- [ ] Documentation complete

## Functional Requirements

- FR-1: O sistema deve persistir `report_emails` em `prb_users` (lista separada por `;`) com validação no Service
- FR-2: O job único deve executar Fase A (por filial) e Fase B (gerencial) conforme automações devidas
- FR-3: Fase A deve filtrar dados exclusivamente pela `branch` do usuário filial e enviar HTML a cada e-mail de `report_emails`
- FR-4: Fase A deve pular filiais sem e-mails com log de aviso, sem abortar o job
- FR-5: Fase B diária deve enviar HTML consolidado aos destinatários administrativos ativos com flag diária
- FR-6: E-mails diários não devem conter anexos; conteúdo em HTML no corpo
- FR-7: Assunto/saudação da Fase A usam nome da filial; da Fase B usam nome do destinatário
- FR-8: Tabelas HTML devem listar notas em atraso e, se houver, notas que vencem no dia de referência; senão texto “Nenhuma nota fiscal nesta situação.”
- FR-9: UI de agendamento deve exibir “Automações” com `display_name`, sem expor `job_id` técnico
- FR-10: Automação das filiais: apenas diário + horário
- FR-11: Automação gerencial: diário / semanal / mensal com campos respectivos; weekly/monthly sem geração de relatório nesta etapa
- FR-12: Persistência via Repository; regras de negócio via Service; tabelas `prb_*` + `_audit`
- FR-13: Logs devem permitir rastrear geração e envio (sucesso/falha) por destinatário/filial

## Non-Goals

- Geração/envio dos relatórios consolidados **semanal** e **mensal** (somente parametrização)
- Importação nova de entregas / mudança da fonte de dados além do necessário para montar as tabelas HTML
- Envio com anexo CSV (removido dos fluxos diários desta feature)
- Cadastro de entidade “Filial” separada de usuários (e-mails ficam no usuário perfil filial)
- Alteração do provedor SMTP / cadastro SMTP (reutilizar o existente)
- Commit automático ou push (implementação na branch atual, commits só se o usuário pedir)

## Design Considerations

- Preservar identidade visual do admin React existente
- Formulário de usuários: textarea ou input de e-mails com helper “separar por ;”
- Schedules: cards/lista de Automações com labels em português; campos condicionais por frequência
- HTML de e-mail: tabelas com bordas simples, alinhamento numérico à direita no Valor, sem frameworks CSS de e-mail complexos

## Technical Considerations

- Stack: Python, FastAPI, React admin, worker CLI, PostgreSQL
- Reutilizar `MailDispatchService`, SMTP padrão e mailer (envio 1:1 por destinatário)
- Critérios de “atraso” e “vence hoje” devem reutilizar a mesma regra de negócio do BI/`limpeza` (documentar mapeamento de colunas: Nota Fiscal, Cliente, Cidade, Valor, Dias em atraso)
- `prb_job_settings` hoje tem `UNIQUE(job_id)`: estender modelo para duas automações (dois `job_id` lógicos apontando ao mesmo executor, ou chave de automação + job compartilhado) sem duplicar a lógica de negócio
- Idempotência: definir runs por fase/automação + `business_date` para não reenviar no mesmo dia sem `--force`
- Branch de trabalho: alterações na **branch atual**; sem commits durante o desenvolvimento Atlas, salvo pedido explícito

## Success Metrics

- Filial recebe apenas seus dados; admin recebe consolidado
- Zero anexos nos e-mails diários após a feature
- Administrador configura as duas automações sem ver nomes técnicos
- Job diário completa mesmo com algumas filiais sem e-mail (apenas warnings)
- Parametrização weekly/monthly salva e exibida corretamente sem gerar relatório indevido

## Open Questions

- Mapeamento exato das colunas do CSV/fonte atual para Nota Fiscal / Cliente / Cidade / Valor / Dias em atraso / “vence hoje” (confirmar nomes de campos em `limpeza`/dataset)
- Texto do remetente “Atenciosamente” — incluir nome/assinatura fixa do Portal ou deixar genérico como no modelo?
- Comportamento se a mesma pessoa estiver em `report_emails` da filial e em destinatários gerenciais (receberá os dois e-mails; ok?)
