# Importação manual de planilhas

## Objetivo

Permitir que administradores atualizem `prb_deliveries` via planilha (CSV/Excel),
como alternativa à API TMS Elite, com validação prévia e histórico auditável.

## Fluxo

```mermaid
flowchart TD
  A[Upload CSV/XLSX/XLS] --> B[Grava arquivo em storage/imports]
  B --> C[Staging prb_import_batch_items]
  C --> D[Validar planilha]
  D -->|erros| E[validated_error — Importar desabilitado]
  D -->|ok| F[validated_ok]
  F --> G[Importar Dados]
  G --> H[Upsert prb_deliveries em transação]
  H --> I[Purge arquivo + progresso]
  I --> J[Snapshot Histórico do dia — replace]
  J --> K[Lote ativo = este batch]
```

Após import bem-sucedida, o sistema **recalcula** o snapshot do **Dashboard Histórico** do dia
(`capture_replace`, `source=manual_import`), substituindo o snapshot anterior da mesma data.
O job `report_overdue_daily` continua usando `capture_if_absent` no horário agendado
(não sobrescreve se o dia já tiver snapshot — inclusive o gerado pelo import).

## Lote ativo (análise BI)

O Operacional, os e-mails e o snapshot **não** leem mais todo o histórico acumulado de `prb_deliveries`. A análise usa o **lote ativo**:

- prioridade: último batch de planilha com status `imported` (`dataset_batch_id`);
- fallback: última sincronização API com sucesso (`dataset_sync_id`);
- a planilha permanece ativa mesmo se a API rodar depois (até o próximo upload).

Cada importação marca as linhas upsertadas com o `batch_id`. Ver [paridade-lote-ativo-macros.md](paridade-lote-ativo-macros.md).

## Acesso

- Somente perfil **admin**
- Menu: **Administração → Importação de Dados**

## Formatos e limites

- `.csv`, `.xlsx`, `.xls`
- Layout compatível com `dados/entregas_relatorio.csv` / `COLUNAS_UTEIS` em `limpeza.py`
- Inclui **Cliente** → `cliente_conta` e **CNPJ Cliente** → `cnpj_cliente`
- Inclui **Nome Pessoa Visita** → `cliente` (destinatário)
- Inclui **Dt. Recebimento** → `dt_recebimento` (campo distinto de **Dt. Entrega**)
- Máximo **20 MB** e **100.000** linhas
- Arquivos retidos em `storage/imports/` (sem purge automático)

## Validação

- Sem escrita em `prb_deliveries` até confirmação
- Estrutura: colunas obrigatórias (`Nro. Entrega`, `Sigla Unidade Entrega`, `Nome Pessoa Visita`) e cabeçalhos duplicados bloqueiam o upload
- Colunas extras do export operacional (fora de `COLUNAS_UTEIS`) são ignoradas — o layout real tem ~80+ campos
- Filial obrigatória e existente em `prb_users` (`profile=filial`, `enabled`)
- Erro de filial sugere cadastro em **Administração → Usuários**
- Duplicidade de `nro_entrega` na planilha, datas/valores inválidos, obrigatórios vazios
- Política **all-or-nothing**: qualquer erro bloqueia a importação

## Importação

- Upsert por `remessa_numero` (mesmo contrato da API/CSV)
- Source: `manual_upload`
- Transação única no lote; falha ⇒ rollback das entregas do lote

## Relatórios / e-mails

O disparo **não** ocorre automaticamente ao fim da importação.

Na tela **Importação de Dados**, use o botão **Disparar Envio de E-mails** (acima do histórico). A UI confirma com mensagem amigável (“Envio de e-mails disparado…”). Em background o servidor executa:

```bash
python -m worker run report_overdue_daily --force
```

(`--force` ignora a janela horária e a idempotência do dia; o conteúdo dos e-mails usa o **lote ativo** atual — última planilha importada ou, na ausência, última sync API.)

API equivalente: `POST /api/imports/dispatch-emails` (admin). Detalhe técnico do processo (pid/job) **não** é exibido ao usuário.

## Tabelas

| Tabela | Uso |
|--------|-----|
| `prb_import_batches` | Lote, progresso, contadores, histórico |
| `prb_import_batch_items` | Staging por linha |
| `prb_import_logs` | Erros de validação |
| `*_audit` | Auditoria |

## API

| Método | Path | Descrição |
|--------|------|-----------|
| POST | `/api/imports/dispatch-emails` | Disparo manual dos e-mails de relatório |
| POST | `/api/imports/upload` | Upload multipart |
| POST | `/api/imports/{id}/validate` | Validação |
| POST | `/api/imports/{id}/import` | Inicia importação |
| GET | `/api/imports/{id}` | Status/progresso |
| GET | `/api/imports` | Histórico (`enabled=true`) |
| GET | `/api/imports/{id}/errors` | Lista de erros |
| DELETE | `/api/imports/{id}` | Exclusão lógica (só `validated_error` / `failed`) |
| POST | `/api/imports/{id}/deactivate` | Exclusão lógica (alias) |

## Cache do arquivo

- Em **sucesso** (`imported`) ou **falha** (`validated_error` / `failed`), o arquivo em `storage/imports/` é removido.
- Após erro, apenas as mensagens permanecem na tela; nova tentativa exige **novo upload**.
- Lotes com erro podem ser removidos do grid via exclusão lógica (`enabled=false`).
