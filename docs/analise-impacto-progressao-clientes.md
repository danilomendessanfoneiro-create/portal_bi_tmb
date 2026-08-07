# Análise de impacto — Progressão, Clientes e processamento (US-001)

**Status:** rascunho técnico para aprovação  
**PRD:** `tasks/prd-evolucao-dashboards-clientes-progressao.md`  
**Data:** 2026-08-07  

> **Gate:** as stories **US-012 a US-015** (schema/captura/aba Progressão / card Pedidos Entregues) **só podem iniciar após este artefato ser aceito** pelo tech lead / produto. US-002–US-011 (calcConsolidada, Status, Clientes, e-mails) podem avançar em paralelo, desde que não criem tabelas de progressão.

---

## 1. Objetivo

Avaliar impacto de:

1. Snapshots de **Progressão** (por upload manual)
2. Cadastro/relatório de **Clientes** (CNPJ)
3. Mudanças de processamento (`calcConsolidada`) e filtros Status / KPIs

…sobre schema PostgreSQL (`prb_*`), performance, Operacional/Histórico, e-mails e compatibilidade com import manual e sync API futura.

---

## 2. Decisões confirmadas (não reabrir na implementação)

| # | Decisão | Valor |
|---|---------|--------|
| 1A | Default do filtro Status | Nenhuma seleção → comportamento atual de pendentes/atraso (sem pré-marcar textos de status) |
| 2A | Gatilho de snapshot de Progressão | **Somente** importação manual bem-sucedida (`status=imported`). Sync API / job diário **não** geram snapshot nesta entrega |
| 3D | Match cliente ↔ entrega | Campo **CNPJ Cliente** → persistir como `prb_deliveries.cnpj_cliente` (dígitos normalizados); match com `prb_clients.cnpj` |
| 4A | UI Progressão | Nova aba no Streamlit (radio: Operacional \| Histórico \| Progressão) |
| — | Chave de comparação Progressão | **`nro_entrega`** (Número da Entrega) |
| — | Pedidos Entregues | `nro_entrega` presente no snapshot anterior e **ausente** no atual (sumiu da planilha) |
| — | Retenção Progressão | **Histórico completo** (sem purge automático nesta entrega) |
| — | Filtro transportadora | **Adiado** |
| — | Fonte de runtime | Somente `prb_*` / lote ativo; sem leitura de planilha/VBA nos dashboards |

---

## 3. Estado atual (baseline)

### 3.1 Snapshots existentes (Histórico — **não** reutilizar para Progressão)

| Tabela | Papel |
|--------|--------|
| `prb_bi_snapshot_run` | 1 foto/dia (`business_date` UNIQUE); `source` ∈ `job`, `seed-demo`, `manual_import` |
| `prb_bi_snapshot_overdue` | **Somente atrasados** da foto; UNIQUE(`snapshot_run_id`, `remessa_numero`) |

- Job: `capture_if_absent` (não sobrescreve o dia).
- Import manual: `capture_replace` no Histórico.
- Histórico **não** guarda evolução de status de todas as entregas; não serve como base da Progressão.

### 3.2 Lote ativo e entregas

- `prb_deliveries` + ponteiro `prb_active_dataset` (migration `030`).
- Operacional / e-mails / regras de prazo leem o **lote ativo** (último import `imported` ou sync API etiquetada).
- Volume de referência em `dados/entregas_relatorio.csv`: ~**3 000** linhas úteis; coluna **`CNPJ Cliente`** já existe na planilha.
- **Não há** `cnpj_cliente` nem `prb_clients` hoje.
- **Não há** campo `transportadora` em `prb_deliveries` (filtro Progressão: adiar ou mapear equivalente depois — ver §8).

### 3.3 Relatórios por e-mail (filial)

- Job `report_overdue_daily` / fase `report_branch_daily`.
- Agrupa por **`filial`** = `user.branch`; destinatários em `prb_users.report_emails`.
- Gerencial: `prb_email_recipients`.
- Layout HTML em adapters de relatório — **reutilizar** para relatório por cliente.

### 3.4 Auditoria

Padrão: colunas `created_by/on`, `modified_by/on`, `enabled` + tabela `prb_*_audit` com trigger `INSERT|UPDATE|DELETE`. Novas entidades devem seguir o mesmo padrão (exceto singleton `prb_active_dataset`, que hoje não tem `_audit`).

---

## 4. Schema proposto (novas tabelas)

### 4.1 Clientes (US-008)

```text
prb_clients
  id SERIAL PK
  name VARCHAR NOT NULL
  cnpj VARCHAR(14) NOT NULL   -- só dígitos; UNIQUE parcial WHERE enabled
  emails TEXT                 -- CSV de e-mails
  created_by/on, modified_by/on, enabled

prb_clients_audit  -- espelho + created_on_audit, action
```

Índices: UNIQUE em `cnpj` entre `enabled=true`; índice em `name` para busca Admin.

### 4.2 Entregas — coluna CNPJ (US-004)

```text
ALTER prb_deliveries ADD cnpj_cliente VARCHAR(14) NULL;
CREATE INDEX ix_prb_deliveries_cnpj_cliente ON prb_deliveries (cnpj_cliente)
  WHERE cnpj_cliente IS NOT NULL AND enabled;
```

Preencher no import (coluna `CNPJ Cliente`) e no mapper API quando o payload trouxer equivalente. Upsert não pode descartar o campo.

### 4.3 Snapshots de Progressão (US-012) — **tabelas novas, dedicadas**

Não misturar com `prb_bi_snapshot_*` (semântica e cardinalidade diferentes).

```text
prb_progress_snapshot_run
  id SERIAL PK
  import_batch_id INTEGER NOT NULL REFERENCES prb_import_batches(id)
  captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  source VARCHAR NOT NULL DEFAULT 'manual_import'
    -- CHECK: nesta entrega só 'manual_import' (reserva valores futuros se API passar a capturar)
  row_count INTEGER NOT NULL DEFAULT 0
  rule_version VARCHAR(40)     -- ex.: calc-consolidada-v1
  notes TEXT NULL
  created_by/on, modified_by/on, enabled
  CONSTRAINT uq_progress_run_batch UNIQUE (import_batch_id)  -- 1 snapshot por batch

prb_progress_snapshot_run_audit

prb_progress_snapshot_item
  id BIGSERIAL PK
  snapshot_run_id INTEGER NOT NULL REFERENCES prb_progress_snapshot_run(id) ON DELETE CASCADE
  nro_entrega VARCHAR(100) NOT NULL
  remessa_numero VARCHAR(100)
  status VARCHAR(100) NOT NULL
  filial VARCHAR(200)
  cliente VARCHAR(500)          -- nome comercial / conta conforme mapeamento
  cnpj_cliente VARCHAR(14)
  cidade_entrega VARCHAR(200)
  uf_entrega VARCHAR(10)
  motorista VARCHAR(300)        -- opcional; útil se transportadora não existir
  valor_total NUMERIC(18,2)
  created_by/on, modified_by/on, enabled
  CONSTRAINT uq_progress_item_run_nro UNIQUE (snapshot_run_id, nro_entrega)

prb_progress_snapshot_item_audit
```

**Índices mínimos (US-012):**

| Índice | Motivo |
|--------|--------|
| `(snapshot_run_id)` | listar itens de um upload |
| `(nro_entrega)` | join entre runs |
| `(snapshot_run_id, nro_entrega)` | UNIQUE + lookup |
| `(cnpj_cliente)` parcial | filtro/relatório cliente |
| `(filial)`, `(status)` | filtros BI |
| `(captured_at)` em `run` | período / retenção |

**Dimensões a materializar no item:** o necessário para filtros da Progressão **sem** join de volta em `prb_deliveries` (o lote ativo muda). Evitar `SELECT *` do raw: gravar só dims usadas na UI/KPI.

#### Por que gravar `nro_entrega` (e impacto)

| Aspecto | Efeito |
|---------|--------|
| Facilita “foi entregue?” | Sim — é a **chave** do anti-join: ontem tinha o número, hoje não tem → Pedidos Entregues |
| Impacto em disco | Baixo por linha (VARCHAR indexado); custo real é **N linhas × N uploads** (histórico completo), não o campo em si |
| Impacto no Operacional / calc | **Nenhum** — snapshot é escrita paralela; não altera `prb_deliveries` nem o cálculo de KPIs |
| Momento da captura | Após o **upsert do batch** e **após `aplicar_regras_macros`**: exclui STATUS TMS `ENTREGUE` e materializa **STATUS PRAZO** (`status_prazo`) com data de referência = dia do `captured_at` |
| Dimensão do gráfico | `status_prazo` (`01_ATRASO` … `05_VENCIMENTO FUTURO`; `(sem prazo)` se sem `dt_prazo_atual`) — coluna TMS `status` permanece só para auditoria |
| Precisa gravar também a lista dos “entregues” no momento? | **Não na v1** — com `nro_entrega` em cada run, o card calcula na leitura (`NOT EXISTS`). Materializar “entregues do dia” só se a query ficar lenta |

Sem `nro_entrega` estável e único por run, a regra de negócio fechada (§8.1) não fecha.

---

## 5. Volume, retenção e performance

### 5.1 Estimativa de volume

| Premissa | Valor |
|----------|--------|
| Linhas/lote (planilha típica) | ~3 000 (amostra atual); planejar pico **10 000–20 000** |
| Uploads manuais/dia | 1–3 (operação); pior caso 5 |
| Retenção | **Histórico completo** (decisão de negócio 2026-08-07) — sem purge automático nesta entrega |
| Crescimento (ordem) | ~3k–20k itens × N uploads; ex.: 2 uploads/dia × 365 × 5k ≈ **3,6M** linhas/ano — ok com índices; monitorar disco/audit |
| Audit item | mesmo ordem de grandeza; se pressionar disco, auditar só o `run` + bulk insert dos itens (R4) |

Espaço bruto (ordem de grandeza): ~0,5–2 KB/linha item → alguns GB/ano no cenário agressivo — aceitável se houver vacuum periódico e monitoramento de disco na VPS.

### 5.2 Política de retenção (fechada)

1. **Manter todo o histórico** de `prb_progress_snapshot_*`; sem job de purge por dias/quantidade nesta entrega.
2. Se no futuro o disco exigir corte, produto define política e aí sim implementar purge (CASCADE nos itens).
3. Progressão pode filtrar período na UI sem apagar dados.
4. **Não** amarrar retenção do Histórico (`prb_bi_snapshot_*`) a esta política — ciclos de vida distintos.

### 5.3 Comparação N×N por `nro_entrega` — precisa materializar?

**Recomendação: não materializar tabela de “transições” na v1.**

| Abordagem | Quando usar |
|-----------|-------------|
| **Agregados por run** (`GROUP BY status` no item) | Gráfico multi-colunas quantidade×status por upload — O(n) por run, barato |
| **Anti-join entre 2 runs consecutivos** | Card Pedidos Entregues: `nro_entrega` em `run_prev` **NOT EXISTS** em `run_curr` (sumiu da planilha = entregue). O(n) com índice `(snapshot_run_id, nro_entrega)` |
| **Join interno** `ON a.nro_entrega = b.nro_entrega` | Evolução de status quando a entrega ainda aparece nos dois uploads |
| **Materializar `prb_progress_transition`** | Só se período com **muitos** runs (&gt;~50) e latência &gt;2–3 s |

Para o período diário/default (poucos uploads), pares consecutivos ordenados por `captured_at` bastam. Evitar produto cartesiano de todos os runs do período: sempre reduzir a **pares ordenados** (run_i → run_{i+1}).

Se no futuro a UI pedir “compare upload A vs B” arbitrário, o mesmo anti-join/join pontual resolve sem tabela de transição.

---

## 6. Impacto por superfície

### 6.1 Operacional

| Mudança | Impacto |
|---------|---------|
| calcConsolidada (US-002) | Regras Python; pode alterar contagens vs calc1/calc2 (exclusão `ENTREGUE`, Status Prazo). Validar paridade com fixture |
| Filtro Status multiselect (US-005) | Default vazio = sem regressão; com seleção, todos os componentes filtram |
| KPIs (US-007) | Remover Valor em Aberto; renomear Em Atraso — só UI se regra já ok |
| Snapshots Progressão | **Nenhum** no Operacional (fonte continua lote ativo) |
| `cnpj_cliente` | Coluna passiva até filtros/relatórios usarem |

### 6.2 Histórico

| Mudança | Impacto |
|---------|---------|
| Continua em `prb_bi_snapshot_*` | Sem mudança de schema obrigatória nesta entrega |
| Filtro Status (US-006) | Filtra detalhe/série sobre atrasados já fotografados; default = hoje |
| Progressão | Aba separada; não misturar métricas |

Risco: usuário confundir “Histórico = atrasos diários” com “Progressão = evolução de status entre uploads”. Mitigar com rótulos/help no Streamlit (US-014/016).

### 6.3 Relatórios filial vs cliente

| | Filial (atual) | Cliente (US-011) |
|--|----------------|------------------|
| Chave | `entrega.filial` = `user.branch` | `entrega.cnpj_cliente` = `client.cnpj` |
| Destinatários | `prb_users.report_emails` | `prb_clients.emails` |
| Layout | HTML existente | **mesmo** template/adapters |
| Skip | sem e-mail / sem match filial | CNPJ inválido, sem e-mail, sem entregas no lote |

Impacto: novo job/fase irmão (não substituir filial). Disparo pós-import pode reutilizar o botão Admin com fase adicional — documentar em US-016.

### 6.4 Upload manual vs API

| Evento | Lote ativo | Snapshot Histórico | Snapshot Progressão |
|--------|------------|--------------------|---------------------|
| Import manual OK | Sim (`remember` batch) | `capture_replace` | **Gravar** run+itens (US-013) |
| Sync API OK | Sim (se política atual) | Conforme job/`capture_if_absent` | **Não** (decisão 2A) |
| Job e-mail | Lê lote ativo | `capture_if_absent` | Não |

Falha do snapshot de Progressão **não** deve reverter o import: log + flag/`notes` no batch ou run parcial (US-013). Schema `source` reservado permite evoluir para API depois sem migration destrutiva.

### 6.5 Processamento calcConsolidada

- Macro exclui linhas `STATUS TMS = ENTREGUE` no AutoFilter antes dos indicadores de prazo.
- Pedidos Entregues (decisão §8.1) inferem conclusão por **ausência** entre planilhas/snapshots consecutivos. O snapshot deve gravar o lote **completo** do upload (linhas persistidas do batch), não o dataframe pós-exclusão de indicadores do Operacional.
- Impedimento se capturar subset parcial ou só atrasados: o anti-join “estava ontem / não está hoje” fica incorreto.

---

## 7. Riscos, impedimentos e recomendações

| ID | Tipo | Descrição | Recomendação |
|----|------|-----------|--------------|
| R1 | Risco | Confundir snapshot Histórico com Progressão | Tabelas `prb_progress_*` dedicadas; docs/UI claras |
| R2 | Risco | Snapshot incompleto impede anti-join “sumiu = entregue” | Capturar de `prb_deliveries` do **batch completo** (tudo que veio na planilha) |
| R3 | Risco | `nro_entrega` duplicado/nulo na planilha | UNIQUE por run; rejeitar/deduplicar na captura; preferir remessa como fallback só se negócio validar |
| R4 | Risco | Histórico completo → audit/disco cresce sem teto | Sem purge na v1; monitorar disco; preferir audit do `run` + bulk insert dos itens se necessário |
| R5 | Impedimento | Sem `cnpj_cliente` na base | US-004 antes de US-011 e filtros Progressão por cliente |
| R6 | Impedimento | Sem `prb_clients` | US-008/009/010 antes de e-mail cliente |
| R7 | Impedimento | Definição de “entregue” | **Fechado:** ausência entre snapshots consecutivos (§8.1), não status textual |
| R8 | Impedimento | Filtro transportadora sem coluna | Adiar na UI ou usar proxy documentado (`motorista` **não** é transportadora) |
| R9 | Perf | Join N×N ingênuo no Streamlit | Pares consecutivos + índices; sem tabela de transição na v1 |
| R10 | Integração | API sem CNPJ no payload | Campo nullable; relatório cliente só casa quando preenchido |
| R11 | Processo | Gate US-012+ | **Bloquear código de Progressão até aceite deste doc** |

**Recomendações estruturais:**

1. Implementar Progressão só após aceite explícito desta análise.
2. Ordem: US-004 → … → US-011; então US-012–015.
3. Na captura (US-013): uma transação de escrita de itens (COPY/executemany) após criar o run; index build já nas migrations.
4. Testes: 2 batches sintéticos; `nro_entrega` só no primeiro batch deve contar no card Pedidos Entregues; o que permanece nos dois não conta.

---

## 8. Perguntas abertas — **fechadas** (2026-08-07)

| # | Pergunta | Decisão |
|---|----------|---------|
| 1 | Como contar **Pedidos Entregues**? | **Por ausência entre snapshots consecutivos**, não por texto de status. Se o `nro_entrega` **estava** no resultado da planilha anterior (ex.: “ontem”) e **não está** no resultado da planilha atual (ex.: “hoje”), conta como entregue. Alinha à consolidada: entregues saem do arquivo; o que some entre uploads = concluído. |
| 2 | Retenção de snapshots Progressão? | **Todo o histórico** — sem purge por dias/quantidade nesta entrega. Monitorar crescimento de disco; purge só se produto pedir depois. |
| 3 | Filtro transportadora? | **Adiar** até existir coluna persistida; não inventar a partir de motorista. |

### Implicações técnicas da decisão 1

- Card Pedidos Entregues (US-015): para cada par de runs consecutivos no período filtrado (`run_prev` → `run_curr`), contar `nro_entrega` presentes em `run_prev` e ausentes em `run_curr`.
- **Não** depender de `status = ENTREGUE` no item atual (a linha tipicamente já não vem na planilha).
- Continua necessário gravar o lote **completo** de cada upload no snapshot (inclui o que ainda está aberto); a “entrega” é inferida na comparação.
- Edge cases a tratar na US-015: primeiro upload do período (sem predecessor → 0); entrega que volta a aparecer depois (reabertura) — fora do card naquele par; filtros (filial/cliente/etc.) aplicados ao conjunto do `run_prev` antes do anti-join.

### Implicações da decisão 2

- Remover da implementação o job de purge 90d/180 runs como requisito; documentar crescimento (~3k–20k linhas × N uploads).
- Índices e `BIGSERIAL` em itens permanecem obrigatórios; audit em massa de itens pode pressionar disco — preferir audit do `run` + insert em lote dos itens se volume reclamar (R4).

---

## 9. Compatibilidade futura (API)

- Coluna `prb_progress_snapshot_run.source` já prevê outros valores; CHECK atual = só `manual_import`.
- Quando quiser snapshot na sync: novo valor `api_sync`, vincular a `dataset_sync_id` (coluna opcional futura em `run`), sem mudar itens.
- `cnpj_cliente` no mapper API é pré-requisito para relatórios cliente em cenário 100% API.

---

## 10. Checklist de cobertura US-001

- [x] Novas tabelas `prb_*` + audit (clientes, progress run/item, `cnpj_cliente`)
- [x] Índices e estratégia de comparação `nro_entrega`
- [x] Retenção e volume
- [x] Impacto Operacional / Histórico / filtros
- [x] Relatórios filial vs cliente
- [x] Upload manual vs API
- [x] Riscos / impedimentos / recomendações (incl. materialização N×N)
- [x] Decisões 2A / chave Progressão / CNPJ Cliente confirmadas
- [x] Gate: US-012+ somente após aceite deste artefato

---

## 11. Aceite

| Papel | Nome | Data | Aceito? |
|-------|------|------|---------|
| Tech lead / produto | Aceite implícito ao solicitar implementação completa do PRD | 2026-08-07 | ☑ |

Após aceite, US-012+ liberadas.
