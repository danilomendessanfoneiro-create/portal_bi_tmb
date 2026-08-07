# Origem dos dados em runtime (checklist)

Consumidores **não** leem CSV/planilha/VBA em runtime para KPIs.

| Consumidor | Fonte |
|------------|--------|
| Operacional (Streamlit) | `prb_deliveries` via lote ativo (`prb_active_dataset`) + regras `calc-consolidada-v1` |
| Histórico | `prb_bi_snapshot_run` / `prb_bi_snapshot_overdue` |
| Progressão | `prb_progress_snapshot_run` / `prb_progress_snapshot_item` |
| E-mails filial/gerencial/cliente | lote ativo + `processar_entregas` / limpeza |
| Import manual / sync API | única escrita a partir de planilha/API |

Macros `calc1.vb` / `calc2.vb` / `calcConsolidada.vb` são referência histórica ou de mapeamento; runtime = `macro_delivery_rules.py`.
