# Paridade: lote ativo × macros Excel

## Objetivo

Garantir que o BI (e e-mails) analisam o **mesmo universo** da última planilha importada, alinhado às macros `calc1`/`calc2`.

## Regra do lote ativo

1. Existe batch `imported` → análise = entregas com `dataset_batch_id` desse batch.
2. Senão → última sync API `success` (`dataset_sync_id`).
3. Senão → vazio (mensagem no BI).

A planilha **permanece** ativa mesmo se a API rodar depois (até novo upload).

`--force` nos e-mails reenvia com base no **lote ativo atual**, não reabre lotes antigos.

## Checklist de homologação

1. Rodar macros no Excel no arquivo X; filtrar `01_ATRASO`; anotar total (ex.: 256).
2. Admin → Importação: upload do **mesmo** arquivo X → Validar → Importar.
3. Abrir BI Operacional: banner “Lote ativo: Planilha — &lt;nome&gt;”.
4. Comparar KPI de atrasados com o total Excel (mesma data de referência / “hoje”).
5. Conferir exclusão das 5 contas (`cliente_conta` / aliases NINFA).

Diferenças residuais: documentar fuso, filtros manuais no Excel ou arquivo diferente.
