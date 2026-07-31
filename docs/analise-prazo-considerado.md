# Análise: campo «Prazo considerado» (Dashboard Operacional)

## Fonte da informação

| Item | Valor |
|------|--------|
| Campo de origem | `dt_prazo_atual` (planilha: **Dt. Prazo Atual**; API/TMS: prazo atual da entrega) |
| Campo derivado | `prazo_considerado` |
| **Não** entra no cálculo | `dt_agendamento` (Dt. Agendamento) |

## Etapa em que a regra é aplicada

1. **Carga / processamento de dados** (`limpeza.processar_entregas`):
   - resolve o **lote ativo** (`ActiveDatasetService`)
   - lê só entregas desse lote em `prb_deliveries`
   - tipa datas
   - chama `calcular_atraso` → `app.services.macro_delivery_rules.aplicar_regras_macros`
2. **Nessa função** o DataFrame recebe:
   ```python
   prazo_considerado = pd.to_datetime(dt_prazo_atual)
   ```
3. **Dashboard Operacional** (`dashboard_controller.render_dashboard`):
   - consome o DataFrame já processado (**não recalcula** atraso)
   - filtro **Prazo considerado** (após normalização):
     - considera só registros **atrasados**
     - compara exclusivamente a **data do prazo** (`prazo_considerado` = Dt. Prazo Atual)
     - intervalo inclusive; só inicial → `prazo >= inicial`; datas iguais → dia exato
     - **não** usa data de importação/atualização
   - KPIs / situação usam as flags `atrasado` / `vence_hoje` / `dias_atraso` das macros

## Lógica vigente (única)

```text
prazo_considerado := dt_prazo_atual   # somente este campo (paridade Excel calc1)

Dt. Prazo Atual < data de referência (hoje)  →  status_prazo = 01_ATRASO  →  atrasado = true
Dt. Prazo Atual = hoje                       →  02_VENCENDO HOJE          →  vence_hoje = true
Dt. Prazo Atual = hoje + 1                   →  03_VENCENDO AMANHÃ
Dt. Prazo Atual = hoje + 2                   →  04_DEPOIS DE AMANHÃ
Dt. Prazo Atual > hoje + 2                   →  05_VENCIMENTO FUTURO

dias_atraso = (hoje − prazo_considerado) se atrasado, senão 0
```

Antes da classificação, o calc1 **remove** 5 contas da coluna Excel **Cliente**
(`cliente_conta` no portal; fallback `remetente` / aliases). Isso **não** usa o destinatário
(`Nome Pessoa Visita` → `cliente`).

A mesma regra vale para:

- Dashboard **Operacional**
- Job de relatório / e-mails
- Snapshot do **Histórico**

O Status TMS (`status`) **não** altera `atrasado`.

## Observação de drift documental

Documentos antigos citavam `prazo_considerado = max(dt_prazo_atual, dt_agendamento)` e um simulador de tolerância no Operacional (`prazo < hoje − N`). Ambos foram descontinuados: a regra vigente é **apenas Dt. Prazo Atual vs hoje**, alinhada às macros Excel.
