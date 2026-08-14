---
title: Automação de coleta diária da planilha no sistema do terceiro
created: 2026-08-13
status: draft
tags: [rpa, playwright, importacao, worker, vps, integracao]
related:
  - "docs/importacao-manual-planilha.md"
  - "docs/servico-jobs.md"
  - "docs/integracao-api-tmselite.md"
  - "app/services/manual_import_service.py"
  - "app/utils/secret_box.py"
  - "robo_extracao/tmb_automation.py"

---

# Plano: Automação de coleta diária da planilha no sistema do terceiro

## Objetivo

Obter diariamente (05:00 America/Sao_Paulo) a planilha no sistema do terceiro via automação de acesso, e alimentá-la no **mesmo** fluxo de upload manual do Portal BI (`ManualImportService`), sem segunda lógica de importação. Resultado observável: lote ativo atualizado antes dos horários de e-mail; dashboards/Progressão alinhados a um upload manual bem-sucedido.

## Contexto

- Relatório **não** disponível de forma adequada por API; manutenção de integração API para esse recorte seria mais complexa neste momento.
- Upload manual já cobre: validação → staging → import → macros → lote ativo → Histórico (`capture_replace`) → Progressão.
- E-mails (`report_overdue_daily`) **não** disparam automaticamente após import; respeitam Automações no Admin.
- VPS já tem timers systemd + `--if-due` (`portal-job-import` / `portal-job-report`).
- Segredos: padrão `encrypt_secret` / `decrypt_secret` (SMTP, token API).
- Progressão hoje: snapshot só em import manual `imported` — reusar o service mantém esse gatilho.
- **Fora de escopo nesta etapa:** implementação de código; PRD formal (pode vir depois da spike).

### Esboço existente (`robo_extracao/`) — 2026-08-14

Substitui Power Automate Desktop: Selenium baixa o Relatório Geral de Entregas no TMS Elite e **depois clica na UI do Admin** (login → Importação → Validar → Importar).

**Não é o caminho-alvo.** Reaproveitar só a etapa 1 (coleta). Descartar a etapa 2 (RPA no Portal BI).

| Parte do esboço | Veredito |
|-----------------|----------|
| URL TMS + `/EntregasRelatorios/RelatorioGeralEntregas` | **Manter** — spike real do caminho |
| `tipoSaida=Excel`, `#btDownload`, hash no nome do arquivo | **Manter** como mapeamento do adapter |
| Selenium + Chrome + `.env` + Task Scheduler Windows | **Não** — VPS/systemd, Playwright, `secret_box` |
| Login + cliques no Admin | **Proibido** — viola “uma regra de processamento”; Admin tem hCaptcha; não espera `imported`; IP hardcoded |

Caminho correto a partir do esboço:

```text
login TMS + download (conhecimento do robo_extracao)
  → bytes/arquivo
  → ManualImportService.upload/validate/start_import   ← NÃO a UI
  → job worker 05:00 na VPS
```


### Fluxo esperado

```text
05:00 → login terceiro → navegação → export → download
     → ManualImportService (upload/validate/start_import)
     → lote ativo + dashboards
     → (horários configurados) → relatórios / e-mails
```

```text
Upload Manual ───────┐
                     ├──> Validação → Importação → Normalização → BI
Automação Terceiro ──┘
```

## Abordagem

**Adapter RPA isolado + orquestrador fino + reuso integral do `ManualImportService`.**

| Alternativa | Decisão |
|-------------|--------|
| Estender API TMS Elite | Rejeitada *por agora* — relatório indisponível / manutenção mais complexa |
| Scraping HTML sem browser | Só se spike achar URL de export autenticada; preferível ao clique, se existir |
| **Playwright headless** | **Escolhido** — downloads nativos, auto-wait, trace/screenshot, estável em Linux VPS |
| Selenium | Reserva; mais verboso e frágil em downloads |
| Segunda lógica de upsert | **Proibida** — uma única regra de processamento |

Arquitetura alvo:

```text
Worker job (05:00)
  → app/integrations/<terceiro>_rpa/   (login/nav/download → bytes)
  → orquestrador
  → ManualImportService.upload / validate / start_import
  → efeitos já existentes
  → report_overdue_daily nos horários atuais (sem force às 05:00)
```

## Passos

### Fase 0 — Spike / go-no-go (obrigatória antes do PRD de build)
- [x] Localizar esboço `robo_extracao/tmb_automation.py` (TMS Elite + RPA Admin) e decidir: reusar só o download
- [x] Conferir vídeo `docs/exemple_plan.mp4` (53s, 14/08/2026) — login, Relatório Geral, Excel, progresso, Download CSV
- [ ] Obter usuário técnico (não `DANILO` pessoal) e autorização formal de automação
- [ ] Classificar login: form simples **sem CAPTCHA visível** no vídeo; confirmar 2FA em outras contas
- [x] Mapear caminho: `/login` → `/home/index` → `/EntregasRelatorios/RelatorioGeralEntregas`
- [x] **Filtro da carga diária:** sem filtros extras — Total → Ver Entregas carrega os Nros sozinho; só Excel + Download
- [ ] Conferir se o CSV `entregas_relatorio-*.csv` = layout do upload manual (`COLUNAS_UTEIS`)
- [ ] Decisão go/no-go documentada neste plano



### Fase 1 — Adapter isolado
- [x] Criar `app/integrations/tmselite_rpa/` (login → Total → Ver Entregas → Excel → Download)
- [x] CLI/dry-run do job: `--dry-run` só baixa
- [x] Artefatos de falha: screenshot em `storage/rpa/traces/`

### Fase 2 — Ponte com upload existente
- [x] Orquestrador chama `upload` → `validate` → `start_import` (aguarda `imported`)
- [x] Actor `job_fetch_tmselite`
- [x] Em `validated_error` / falha de import: não chama import; falha o job


### Fase 3 — Credenciais e schedule VPS
- [x] Persistência cifrada (padrão `secret_box`) — URL, usuário, senha na tela Automações
- [x] Seed Automações `fetch_tmselite_spreadsheet` 05:00 (inativo até senha)
- [x] Job worker Playwright + `--if-due` / `--force` / `--dry-run`
- [x] Unit/timer systemd (portal-job-import dispara a coleta TMS e o import API com `--if-due`) + `playwright install chromium` no deploy
- [x] Idempotência: 1 sucesso/dia; `--force` para reprocessar

### Fase 4 — Falhas, logs e monitoramento
- [ ] Tabela de runs (estilo `prb_integration_logs`): início/fim, status, etapa, arquivo, batch_id, contagens, erro
- [ ] Tratamento explícito: login, indisponibilidade, UI alterada, export, download, validação, import
- [ ] Alertas operacionais (e-mail admin / runbook); e-mails de relatório continuam no job existente
- [ ] Doc runbook VPS (comandos, traces, reexecução)

### Fase 5 — Admin opcional
- [ ] Tela config + “Executar agora” + histórico do último run
- [ ] Converter plano maduro em PRD (`/prd`) se for executar via Atlas

## Riscos & Mitigações

- CAPTCHA / MFA / ToS → spike precoce; autorização escrita; possível No-go
- UI do terceiro muda → seletores centralizados; smoke; traces; orçamento de manutenção 1–4 h/quebra
- Layout da planilha muda → já coberto pela validação do upload manual
- Import assíncrono no service → job deve aguardar status final antes de sucesso
- Disparo de e-mail às 05:00 → **não** fazer; respeitar Automações
- Job API `import_deliveries_*` compete com planilha → definir prioridade do lote ativo (hoje planilha prevalece até próximo upload)
- Dependências Chromium na VPS → incluir no deploy/docs

### Achados do vídeo `docs/exemple_plan.mp4` (2026-08-14)

~53 s. Sem CAPTCHA/2FA na tela. Login `DANILO` (Todas as unidades).

| Tempo | O que aparece |
|-------|----------------|
| 0–2 s | OBS |
| 2–6 s | `.../login?ReturnUrl=%2F` — campos **INFORME O SEU LOGIN** / **PREENCHA SUA SENHA**, botão **Processando...**, depois **Liberando menus e módulos...** |
| 6–18 s | `.../home/index` Painel de Controle |
| ~18 s | Clique no Total de **Cenário Entregas** → modal **Detalhamento das Entregas** → **Ver Entregas (2383)** |
| 20 s+ | `.../EntregasRelatorios/RelatorioGeralEntregas` |
| 22–24 s | **Exibir = Excel** (obrigatório p/ este tipo de busca — faixa vermelha) |
| 26–46 s | **Buscar** → **Processando...** + barra 20%→80% (tabela na tela fica vazia — export só Excel) |
| 48–50 s | Barra **100%** + botão verde **Download** |
| 50 s | Chrome baixa `entregas_relatorio-00360-d80f20bd1abc497ba9bfd254ca3a76ae.csv` (~1,7 MB) |

Regras da tela (faixas azuis): período obrigatório; **máx. 62 dias**. No vídeo as datas ficaram vazias e o download mesmo assim ocorreu — porque o tipo de busca era **Nro. Entrega** com lista colada (não é o recorte da carga diária).

Ajuste vs `tmb_automation.py`: não basta clicar `#btDownload` na hora; esperar **Processando** + barra 100% e então o botão verde **Download**. Arquivo é **CSV** (nome `entregas_relatorio-<codigo>-<hash>.csv`), não necessariamente XLSX.

**Confirmado pelo vídeo + usuário (2026-08-14):** a carga diária **não** preenche filtros de data. Fluxo:

```text
Login TMS
  → Painel de Controle
  → clique em Total (Cenário Entregas)
  → modal Detalhamento das Entregas
  → Ver Entregas (N)
  → Relatório Geral já preenchido com os Nros
  → Exibir = Excel  (obrigatório; sem outros filtros)
  → Buscar → Processando (barra 0–100%)
  → botão verde Download
  → CSV entregas_relatorio-<codigo>-<hash>.csv
  → ManualImportService (não a UI do Admin)
```

Configuração (Admin → Automações, job `fetch_tmselite_spreadsheet`): horário 05:00, URL, usuário, senha cifrada (`secret_box`). Seed inativo até preencher senha. Job Playwright ainda não implementado.

## Questões em aberto

- URL e nome exato do sistema do terceiro (homolog vs produção)? **Produção vista:** `https://tmblogistica.tmselite.com`
- Credenciais técnicas e política de 2FA/CAPTCHA? **Localizadas** em `robo_extracao/.env.example` (`TMB_USER`/`TMB_PASS`, conta **DANILO**, sem CAPTCHA no vídeo). Ainda é conta pessoal — preferir usuário técnico na VPS. Senha **não** deve ficar no example versionado; produção usa `secret_box`. `ADMIN_*` vazio — correto (não logar no Admin via RPA).
- Arquivo idêntico (colunas/filtros) ao upload manual atual? **Falta** comparar o CSV baixado
- **Carga diária: exportar por período (qual campo de data?) ou repetir o fluxo do painel (lista de Nros)?** **Fechado:** fluxo do painel (Total → Ver Entregas), sem filtros extras.
- Uma coleta/dia às 05:00 basta para Progressão, ou precisa 2ª corrida?
- Uma coleta/dia às 05:00 basta para Progressão, ou precisa 2ª corrida?
- Quem recebe alerta de falha da automação?
- Retenção de arquivos/traces em `storage/`?
- Manter, pausar ou desligar `import_deliveries_daily` após go-live desta automação?
- Rodar em feriados?
- Sanitizar `.env.example` do `robo_extracao` — **feito 2026-08-14** (placeholders; senha só em `.env` local / `secret_box`)


## Decisões fechadas (análise 2026-08-13)

1. Viável tecnicamente, com risco principal na estabilidade da UI do terceiro.
2. Playwright recomendado; Selenium só reserva.
3. Isolar acesso ao terceiro; **proibido** duplicar processamento.
4. Credenciais com `secret_box` (igual SMTP/API).
5. E-mails nos horários já parametrizados, não acoplados às 05:00.
6. Implementação só após Fase 0 (spike) positiva.
7. `robo_extracao/` é protótipo de coleta, não arquitetura de produção: **não** automatizar a UI do Admin; importar via `ManualImportService`.
8. Fluxo operacional = Total → Ver Entregas → Relatório pré-carregado → Excel → Download (sem filtros).
9. Credenciais TMS na tela Automações (`fetch_tmselite_spreadsheet`), senha via `secret_box`.

