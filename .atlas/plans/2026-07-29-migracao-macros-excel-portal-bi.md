---
title: Migração macros Excel (calc1/calc2) para Portal BI
created: 2026-07-29
status: draft
tags: [architecture, data-pipeline, excel-migration, tmselite]
related: ["tasks/prd-integracao-api-tmselite.md", "calc1.vb", "calc2.vb", "limpeza.py"]
---

# Plano: Migração macros Excel (calc1/calc2) para Portal BI

## Objetivo
Eliminar a dependência das macros VBA (`calc1.vb` / `calc2.vb`) reproduzindo no Portal BI o mesmo resultado tratado que o cliente usa hoje para análise, integrado ao fluxo API TMS → Postgres → dashboards/relatórios.

## Contexto
Hoje o cliente: importa bruto no Excel → roda `F_DEMAIS_CLIENTE_1` (`calc1`) → roda `F_DEMAIS_CLIENTE_2` (`calc2`) → analisa o resultado. O Portal já importa API para `prb_deliveries` e calcula atraso em `limpeza.py`, mas **as regras não são equivalentes às macros** (prazo, exclusão de clientes, Retorno Filial). Cosméticos Excel (cores, bordas, freeze) ficam fora do escopo.

### Achados da engenharia reversa (resumo)

**calc1 — regras de negócio reais**
1. Seleção de colunas brutas (whitelist).
2. Colunas derivadas vazias: `Prazo` (depois `STATUS PRAZO`) e `RETORNO FILIAL`.
3. Aba auxiliar `RETORNOS` (Nota Fiscal → Retorno Filial) + `PROCV` — **enriquecimento manual externo**.
4. Exclusão de 5 clientes fixos (NINFA, MINAS MAIS, PREDILECTA, SO FRUTA, STELLA DORO).
5. Classificação `STATUS PRAZO` só com `DT. PRAZO ATUAL` vs hoje: `01_ATRASO` … `05_VENCIMENTO FUTURO`.
6. Renomes/ordem de colunas para o layout final de 12 campos.

**calc2**
- Só limpa colunas extras e força a ordem final das 12 colunas. Sem regra nova.

**Gap vs Portal atual (`limpeza.py`)**
- Portal: `prazo_considerado = max(dt_prazo_atual, dt_agendamento)`; exclui entregue/cancelada.
- Macro: só `Dt. Prazo Atual`; não filtra entregue/cancelada no Status Prazo.
- Portal não aplica exclusão dos 5 clientes nem Retorno Filial.

## Abordagem
Arquitetura em **duas camadas persistidas** (bruto + tratado) + pipeline Python (Pandas, já no stack) após o job de importação API. Alternativas: Polars (ganho marginal, custo de troca), só SQL (pior para regras tabular/lookup), materializar só views (não versiona histórico de transformação). Validação por golden dataset: Excel pós-macros vs Python linha a linha.

## Passos
- [x] Fase 1 — Inventário formal das regras (matriz coluna a coluna calc1/calc2 ↔ campos API/CSV)
- [x] Fase 2 — Documentar transformações + lista de exclusões + contrato `STATUS PRAZO` + origem de Retorno Filial
- [x] Fase 3 — Implementar regras macros em Python (`macro_delivery_rules` + limpeza)
- [x] Fase 3b — Retorno Filial vazio (confirmado: não usam)
- [ ] Fase 4 — Golden test: export Excel pós-macros vs output Python (diff de chaves)
- [ ] Fase 5 — Encadear transform persistido pós-import API (opcional; hoje on-read)
- [ ] Fase 6 — Remover caminho Excel/macros da operação; manter script CSV só como fallback de teste

## Riscos & Mitigações
- Retorno Filial depende de planilha manual `RETORNOS` → cadastrar tabela admin + seed a partir do Excel atual; sem isso a paridade falha.
- Divergência prazo macro vs regra já acordada no Portal (`max` + excluir entregue) → decidir com o cliente qual é a fonte da verdade (paridade Excel vs regra BI atual).
- Classificação Status Prazo usa `Date` do Excel (sem hora) → normalizar datas para `.date()` em Python.
- Exclusão de clientes hardcoded → config em banco para não redeployar.

### Decisões fechadas
- **Retorno Filial (2026-07-30):** coluna existe na macro, mas **não usam** → no Portal permanece **vazia**. Sem cadastro RETORNOS / Admin nesta fase.
- **Paridade Excel 100%** para STATUS PRAZO (só `dt_prazo_atual`) + exclusão dos 5 clientes do calc1.
- Implementação: `app/services/macro_delivery_rules.py` + `limpeza.calcular_atraso`.

## Questões em aberto
- O layout de 12 colunas da macro é só para Excel do cliente ou o Admin/BI também deve espelhar esses nomes?
- Persistência em tabela tratada separada (`prb_deliveries_treated`) vs transform on-read (hoje: on-read via limpeza)?

