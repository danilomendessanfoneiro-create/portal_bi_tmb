# Mapeamento calcConsolidada.vb → Python

Fonte de verdade: `calcConsolidada.vb`. `calc1.vb` / `calc2.vb` são histórico e **não** definem regras em runtime.

## Regras de negócio (runtime)

| Regra VBA | Python |
|-----------|--------|
| AutoFilter `STATUS TMS` = `ENTREGUE` e exclusão das linhas | `excluir_status_entregue` em `macro_delivery_rules.py` |
| Status Prazo vs `Dt. Prazo Atual` / hoje (01…05) | `classificar_status_prazo` |
| Retorno Filial (coluna vazia / não usada) | `retorno_filial = ""` |
| Prazo considerado = Dt. Prazo Atual | `prazo_considerado` ← `dt_prazo_atual` |
| Cosmético Excel (bordas, freeze, rename headers) | **Não** reproduzido |

## Removido vs calc1/calc2

Exclusão por lista de contas (`CLIENTES_EXCLUIR_MACROS` / coluna Cliente) **não** existe na consolidada e foi **retirada** do caminho `aplicar_regras_macros`.

## Pipeline

`limpeza.calcular_atraso` → `aplicar_regras_macros` (versão `calc-consolidada-v1`).

## Indicadores-chave (paridade)

No mesmo arquivo, após consolidada:

- Linhas com status `ENTREGUE` não entram nos KPIs de aberto/atraso
- `atrasado` ⇔ `status_prazo == 01_ATRASO`
- `vence_hoje` ⇔ `status_prazo == 02_VENCENDO HOJE`

Fixture: `tests/test_macro_delivery_rules.py`.
