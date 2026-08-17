# Release — Automações por dia + coleta TMS + monitoramento técnico

Data de referência: **2026-08-14**  
Branch de trabalho: `develop` → publicar em **`master`** na VPS (`/opt/portal-bi-tmb`).  
PRD: `tasks/prd-reestruturacao-automacoes-monitoramento.md`  
Jobs/detalhes: [`servico-jobs.md`](servico-jobs.md) · Runbook geral: [`deploy-vps.md`](deploy-vps.md)

## O que entra nesta release

| Área | Mudança |
|------|---------|
| Banco | Migrations **040** (credenciais TMS no job), **041** (`run_weekdays`), **042** (`duration_ms`, `error_step`) |
| Automações (Admin) | Só 4 robôs visíveis; dias da semana; feedback salva sucesso/erro; menu Integração API oculto |
| Scheduler | `--if-due` exige **ativo + dia ∈ run_weekdays + horário** e só na **janela de 60 min** após `local_time` (depois: e-mail + `--force` manual) |
| Coleta TMS | Job Playwright `fetch_tmselite_spreadsheet` → import via fluxo manual |
| Monitoramento | E-mail técnico após success/failed (`TECH_SMTP_*` só no `.env`); corpo com **Ambiente** (`APP_ENV`), métricas e **MOTIVO DA FALHA** |
| Relatórios | Uma tabela HTML **Notas Fiscais em atraso**; `Dias em atraso = 0` = vence hoje |
| SMTP operacional | Porta **465** usa SSL implícito; ponte Gmail temporária se o mail TMB não alcançar a VPS (ver `docs/diagnostico-smtp-tmb-vps.md`) |
| Timers | `portal-job-import` roda TMS `--if-due` e depois API daily `--if-due` (API continua desativada por seed) |

## Pré-requisitos antes do deploy

- [ ] Código desta release commitado e em `master` (ou branch que a VPS puxa)
- [ ] Backup Postgres na VPS (`pg_dump`)
- [ ] Senha de app Gmail pronta para `TECH_SMTP_PASSWORD` (não commitada)
- [ ] Credenciais TMS Elite para a tela Automações (URL/usuário/senha)

## Deploy na VPS (comandos)

```bash
# 1) Backup
sudo -u postgres pg_dump portal_bi_tmb | gzip > ~/backup-portal_bi_tmb-$(date +%F).sql.gz

# 2) Atualizar código + deps + Playwright + migrations 040–042 + build Admin
cd /opt/portal-bi-tmb
./deploy/update.sh --branch master --with-units

# 3) SMTP técnico no .env (se ainda não existir)
sudo -u www-data nano /opt/portal-bi-tmb/.env
# acrescentar TECH_SMTP_* (ver .env.example); TECH_SMTP_PASSWORD=senha-de-app
# NÃO versionar a senha.

# 4) Reinício (update.sh já reinicia; se só mexeu no .env:)
sudo systemctl restart portal-api portal-bi
sudo systemctl restart portal-job-report.timer portal-job-import.timer
sudo systemctl daemon-reload
sudo systemctl list-timers | grep portal-job

# 5) Smoke
curl -s http://127.0.0.1:8000/api/health
# Abrir /admin/ → Automações (4 cards, dias da semana)
```

Confirmar migrations aplicadas:

```bash
sudo -u postgres psql -d portal_bi_tmb -c \
  "SELECT filename FROM prb_schema_migrations WHERE filename LIKE '04%' ORDER BY 1;"
# Esperado: 040_..., 041_..., 042_...
```

## Pós-deploy funcional (Admin)

1. **Automações** — ligar só o que deve rodar em produção; conferir horário e dias (seg–sáb).
2. **Coleta TMS** — URL, usuário, senha; testar:
   ```bash
   sudo -u www-data /opt/portal-bi-tmb/.venv/bin/python -m worker run fetch_tmselite_spreadsheet --dry-run
   ```
3. **Relatórios** — SMTP da tela ativo; filiais/clientes/gerencial com e-mails.
4. **Monitoramento** — após um `--force` controlado, conferir caixa `TECH_SMTP_TO` (métricas + motivo em falha).
5. Jobs da **API** e menu Integração API permanecem ocultos; não reativar se a coleta for via planilha TMS.

## Testes rápidos sugeridos

```bash
# Agenda respeitada (se desativado ou fora do dia → skipped)
sudo -u www-data /opt/portal-bi-tmb/.venv/bin/python -m worker run fetch_tmselite_spreadsheet --if-due
sudo -u www-data /opt/portal-bi-tmb/.venv/bin/python -m worker run report_overdue_daily --if-due

# Forçar só quando combinado (gera lote / e-mails reais)
# sudo -u www-data ... -m worker run fetch_tmselite_spreadsheet --force
# sudo -u www-data ... -m worker run report_overdue_daily --force
```

## Rollback

```bash
cd /opt/portal-bi-tmb
git log --oneline -5
git checkout <commit-anterior>
./deploy/update.sh --skip-migrate   # ou migrate só se o commit antigo exigir
```

Migrations **040–042** já aplicadas **não** devem ser revertidas sem plano de DBA. Desligar robôs na tela Automações mitiga impacto imediato.

## Arquivos-chave

- `database/migrations/040_add_tms_rpa_job_settings.sql`
- `database/migrations/041_add_job_run_weekdays.sql`
- `database/migrations/042_add_job_run_duration_and_error_step.sql`
- `app/services/tech_monitor_service.py`
- `app/services/tms_spreadsheet_fetch_service.py`
- `worker/jobs/fetch_tmselite_spreadsheet.py`
- `frontend/src/pages/SchedulePage.tsx`
- `deploy/systemd/portal-job-import.service`
- `.env.example` (`TECH_SMTP_*`)
