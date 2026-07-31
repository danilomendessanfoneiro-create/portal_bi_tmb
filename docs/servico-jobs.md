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
- `--if-due` — avalia cada automação independentemente (horário + frequência)
- `--date YYYY-MM-DD` — data de negócio (default: hoje America/Sao_Paulo)

Artefato local (auditoria, **não** anexado ao e-mail): `storage/reports/YYYY-MM-DD/atrasos_consolidado.csv`

## Job único + duas automações

O CLI `report_overdue_daily` orquestra duas fases:

| Automação (`job_id` interno) | Destinatários | Conteúdo | Frequência |
|---|---|---|---|
| `report_branch_daily` | E-mails no cadastro do usuário **filial** (`report_emails`, separados por `;`) | Só dados da filial | Diário |
| `report_managerial` | Destinatários administrativos (`prb_email_recipients`) | Consolidado | Diário / semanal / mensal (UI) |

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

## Pré-requisitos para envio real

1. SMTP padrão ativo em Configurações → SMTP
2. Usuários filial com `report_emails` (Fase A)
3. Destinatários com “relatório diário” ativos (Fase B)
4. Migrations aplicadas até `019`
5. Configuração padrão em **Integração API** + dados em `prb_deliveries`

## Admin

- Usuários → perfil filial → campo **E-mails do relatório**
- Configurações → **Automações** (nomes amigáveis; sem expor IDs técnicos)

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
| `portal-job-import.timer` | `import_deliveries_daily --if-due` |

Os timers disparam a cada 15 minutos; o worker com `--if-due` respeita o horário de cada automação no Admin. Carga inicial: `import_deliveries_initial --force` (manual, one-shot).

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
