# Worker jobs — Portal BI TMB

## CLI (local)

```bash
# na raiz do repo, com venv ativado
python -m worker list
python -m worker run import_deliveries
python -m worker run report_overdue_daily --dry-run
python -m worker run report_overdue_daily --date 2026-07-28 --force
python -m worker run report_overdue_daily --if-due
```

Flags:
- `--dry-run` — gera CSV de auditoria e simula fases **sem** enviar e-mail (não grava success de idempotência)
- `--force` — ignora idempotência do dia (por automação)
- `--if-due` — avalia cada automação: **ativo + dias da semana (`run_weekdays`) + horário** no timezone do job
- `--date YYYY-MM-DD` — data de negócio (default: hoje America/Sao_Paulo)

Artefato local (auditoria, **não** anexado ao e-mail): `storage/reports/YYYY-MM-DD/atrasos_consolidado.csv`

## Automações visíveis (Admin)

Tela **Configurações → Automações**. O menu **Integração API** e os jobs de API **não aparecem** (código e tabelas permanecem).

| job_id | Nome na tela | Horário padrão | Dias padrão | Ativo padrão |
|---|---|---|---|---|
| `fetch_tmselite_spreadsheet` | Coleta da planilha TMS Elite | 05:00 | seg–sáb | Não |
| `report_branch_daily` | Envio Diário de Relatórios das Filiais | 08:00 | seg–sáb | Não |
| `report_client_daily` | Envio Diário de Relatórios dos Clientes | 08:00 | seg–sáb | Não |
| `report_managerial` | Relatório Gerencial | 08:00 | seg–sáb | Não |

`run_weekdays`: 0=Domingo … 6=Sábado. Domingo desmarcado por padrão.

**Regra dos robôs:** só executam via `--if-due` se `enabled` **e** o dia está em `run_weekdays` **e** o relógio local já passou de `local_time`.

Jobs ocultos (desativados): `import_deliveries_daily`, `import_deliveries_initial`.

## Monitoramento técnico

Cada execução **success/failed** dos quatro robôs visíveis grava `prb_job_runs` (`duration_ms`, `error_step`, `metrics_json`) e envia um e-mail técnico (SMTP **só por env**, não o SMTP da tela). `skipped` não envia.

Variáveis (`.env` / systemd): `TECH_SMTP_HOST`, `TECH_SMTP_PORT`, `TECH_SMTP_USER`, `TECH_SMTP_PASSWORD`, `TECH_SMTP_FROM`, `TECH_SMTP_FROM_NAME`, `TECH_SMTP_TO`. Sem senha, o job de negócio segue e o e-mail é ignorado (log).

Assunto (sucesso): `Portal BI – Relatório de Execução das Automações – DD/MM/YYYY`.
Assunto (falha): `Portal BI – FALHA – Relatório de Execução das Automações – DD/MM/YYYY`.
Corpo: robô, identificador, run id, resultado, horários, duração e métricas (lote/arquivo/e-mails etc.). Em falha, bloco **MOTIVO DA FALHA** com etapa, motivo e detalhes.

## Job único + fases de relatório

O CLI `report_overdue_daily` orquestra três fases:

| Automação (`job_id` interno) | Destinatários | Conteúdo | Frequência |
|---|---|---|---|
| `report_branch_daily` | E-mails no cadastro do usuário **filial** (`report_emails`, separados por `;`) | Só dados da filial | Dias + horário no Admin |
| `report_client_daily` | E-mails do cadastro **Clientes** | Por CNPJ | Dias + horário no Admin |
| `report_managerial` | Destinatários administrativos (`prb_email_recipients`) | Consolidado | Dias + horário no Admin |

- E-mail em **HTML no corpo**, sem anexo.
- Assunto filial: `Relatório de Entregas - [Filial]`
- Assunto gerencial: `Relatório de Entregas - [Nome do destinatário]`
- Colunas da tabela: Nota Fiscal, Cliente, Cidade, Dt. Agendamento, Ult. Motorista, Dias em atraso
- Valores vazios de data/motorista → célula em branco (sem `NaT` / `nan`)
- Filial sem e-mails: log de aviso e pula (não falha o job).
- Semanal/mensal do gerencial: **somente parametrização** nesta etapa (log se `--if-due` disparar).

Jobs auxiliares:

| job_id | Status |
|--------|--------|
| `import_deliveries` | Alias da atualização diária |
| `import_deliveries_initial` | Carga inicial API (initial_load_days) |
| `import_deliveries_daily` | Sync diário por dataCadastro |
| `report_overdue_daily` | Executor das duas fases de e-mail |
| `fetch_tmselite_spreadsheet` | Coleta Playwright da planilha TMS (Total → Ver Entregas → Excel) e importa via `ManualImportService` |

```bash
python -m worker run fetch_tmselite_spreadsheet --dry-run
python -m worker run fetch_tmselite_spreadsheet --force
```

Pré-requisitos: migrations `041`/`042`, Chromium (`playwright install chromium`), credenciais em Automações → Coleta da planilha TMS Elite (ativo + dia/horário). `--dry-run` baixa o arquivo e **não** importa.


## Pré-requisitos para envio real

1. SMTP padrão ativo em Configurações → SMTP
2. Usuários filial com `report_emails` (Fase A)
3. Destinatários com “relatório diário” ativos (Fase B)
5. Migrations aplicadas (inclui `041` dias da semana e `042` duração/etapa do run)
6. SMTP técnico (`TECH_SMTP_*`) se quiser o e-mail de monitoramento; SMTP da tela continua só para relatórios de atraso

## Admin

- Usuários → perfil filial → campo **E-mails do relatório**
- Configurações → **Automações** (nome amigável, horário, dias da semana, ativo; banner de sucesso/erro ao salvar). Coleta TMS: URL, usuário e senha cifrada. Jobs da API e Integração API ocultos.
- Deploy desta release: [release-automacoes-monitoramento.md](release-automacoes-monitoramento.md)

## VPS (systemd)

```bash
sudo cp deploy/systemd/portal-job-report.service /etc/systemd/system/
sudo cp deploy/systemd/portal-job-report.timer /etc/systemd/system/
sudo cp deploy/systemd/portal-job-import.service /etc/systemd/system/
sudo cp deploy/systemd/portal-job-import.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now portal-job-report.timer portal-job-import.timer
sudo systemctl list-timers | grep portal-job
```

| Timer | Job |
|-------|-----|
| `portal-job-report.timer` | `report_overdue_daily --if-due` (também grava snapshot histórico antes do e-mail) |
| `portal-job-import.timer` | `fetch_tmselite_spreadsheet --if-due` e em seguida `import_deliveries_daily --if-due` |

Os timers disparam a cada 15 minutos; `--if-due` respeita ativo + dias + horário. Jobs da API no `portal-job-import` não disparam enquanto `enabled=false`. Carga inicial API: `import_deliveries_initial --force` (manual, one-shot; job oculto).

O disparo manual de e-mails **não** é automático após import de planilha. No Admin → Importação de Dados, o botão **Disparar Envio de E-mails** chama em background:

```bash
python -m worker run report_overdue_daily --force
```

(`--force` ignora a janela horária; o conteúdo usa o **lote ativo** — ver [importacao-manual-planilha.md](importacao-manual-planilha.md) e [paridade-lote-ativo-macros.md](paridade-lote-ativo-macros.md).)

## Snapshots históricos (BI Histórico)

Antes dos e-mails, `report_overdue_daily` grava um snapshot em `prb_bi_snapshot_run` / `prb_bi_snapshot_overdue` via `capture_if_absent` (1× por `business_date` se ainda não existir). A aba **Histórico** no Streamlit consome essas tabelas.

A **importação manual** de planilha **recalcula** o snapshot do dia (`capture_replace`), alinhado ao lote ativo da planilha. O job agendado **não** sobrescreve se o dia já tiver snapshot.

### Lote ativo

Operacional, e-mails e captura pós-import leem somente o lote ativo (`dataset_batch_id` da última planilha `imported`, ou `dataset_sync_id` da última sync API). Detalhes: [paridade-lote-ativo-macros.md](paridade-lote-ativo-macros.md).

### Detalhe do dia (drill-down)

Na aba **Histórico**, o usuário pode **clicar numa barra** (ou usar o selectbox **Dia para detalhar**) para abrir o **Detalhe do dia**:

- Fonte: somente `prb_bi_snapshot_overdue` da `business_date` (atrasados da foto)
- KPIs: qtde em atraso, valor total, média de dias em atraso
- Breakdown por filial (admin) ou cliente (perfil filial), com drill por clique
- Tabela ordenada por `dias_atraso` desc, incluindo `status_prazo`
- **Não** reconstrói “vence hoje” / “em dia” a partir de `prb_deliveries`

PRD: `tasks/prd-drilldown-dashboard-historico.md` · plano: `.atlas/plans/2026-07-31-drilldown-dashboard-historico.md`

Demo (dados fake, não mistura com `source=job`):

```bash
python database/deploy/seed_bi_snapshot_demo.py --days 30 --replace-demo
```

Ver PRD: `tasks/prd-bi-historico-snapshots.md`

Ver PRD: `tasks/prd-ajustes-envio-relatorios-automacoes.md`
