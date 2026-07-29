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
| `import_deliveries` | Stub (API futura) |
| `report_overdue_daily` | Executor das duas fases |

## Pré-requisitos para envio real

1. SMTP padrão ativo em Configurações → SMTP
2. Usuários filial com `report_emails` (Fase A)
3. Destinatários com “relatório diário” ativos (Fase B)
4. Migrations aplicadas até `013`

## Admin

- Usuários → perfil filial → campo **E-mails do relatório**
- Configurações → **Automações** (nomes amigáveis; sem expor IDs técnicos)

## VPS (systemd)

```bash
sudo cp deploy/systemd/portal-job-report.service /etc/systemd/system/
sudo cp deploy/systemd/portal-job-report.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now portal-job-report.timer
sudo systemctl list-timers | grep portal-job
```

O timer dispara a cada 15 minutos; o worker com `--if-due` respeita cada automação.

Ver PRD: `tasks/prd-ajustes-envio-relatorios-automacoes.md`
