# Integração API TMS Elite → Persistência local (BI TMB)

Documento de trabalho para a migração da fonte `dados/entregas_relatorio.csv`
para a API de terceiros. Baseado apenas em:

- Contrato/sample de resposta: [`model.json`](../model.json)
- Uso atual no BI: [`limpeza.py`](../limpeza.py), [`app.py`](../app.py), [`auth.py`](../auth.py)
- Endpoint informado (ainda **sem acesso** autenticado neste ambiente)

Status: **rascunho técnico** — depende de respostas do fornecedor e de um
sample real do tenant TMB.

---

## 1. Endpoint conhecido

```
GET https://endpoint.tmselite.com/api/v1/entregas/relatorios/geral
  ?dataCadastroInicio=2025-05-01
  &dataCadastroFim=2025-05-27
  &idStatus=
  &idServico=
  &currentPage=1
  &pageSize=500
```

Observações:

- Hoje o link **não acessa** daqui (auth / rede / credenciais desconhecidas).
- Query params sugerem filtros por **data de cadastro**, status e serviço,
  com paginação (`currentPage`, `pageSize`).
- Envelope do response (sample): `pager`, `code`, `message`, `results[]`.

### O que ainda falta para consumir

| Item | Situação |
|---|---|
| URL base / ambiente (homolog vs prod) | Só o host acima |
| Auth (API key, Bearer, Basic, IP allowlist) | Desconhecido |
| Headers obrigatórios | Desconhecido |
| TLS / certificado | Desconhecido |
| Rate limit | Desconhecido |
| `pageSize` máximo real | Sample usa 500 |
| Contrato OpenAPI / Swagger | Não disponível |
| Sample JSON do **tenant TMB** | Só sample genérico em `model.json` (AGV/FEDEX) |

---

## 2. Por que persistir do nosso lado

A API é paginada e filtrada por janela de cadastro. O dashboard precisa de:

- Universo estável para recalcular atraso com “hoje” (Brasília)
- Histórico além da janela da última chamada
- Performance (Streamlit não deve paginar a API a cada clique)
- Auditoria / paridade CSV × API na fase de transição
- Campos derivados (`atrasado`, `dias_atraso`, `prazo_considerado`, etc.)

**Proposta:** job de sync (batch) grava/atualiza uma tabela local; o portal
lê só a base local (substituindo `carregar_dados_brutos` do CSV).

```
API TMS Elite  --(sync job)-->  persistência local  --(limpeza/atraso)-->  dashboards
```

---

## 3. Modelo de persistência proposto

Sugestão: **uma tabela flat** alinhada ao pipeline atual (`COLUNAS_UTEIS` +
metadados de sync). Pode ser SQLite, Postgres ou Parquet; o importante é o
contrato de colunas.

### 3.1 Tabela `entregas` (fato para o BI)

Chave natural sugerida: `nro_entrega` (confirmar se = `pedidos.numero`).

| Coluna local | Tipo sugerido | Origem API (`results[]`) | Obrigatório p/ BI? | Notas |
|---|---|---|---|---|
| `nro_entrega` | TEXT PK | `pedidos.numero` | Sim | Cast int→str |
| `nro_arquivo` | TEXT NULL | `arquivo.numero` | Não | Útil p/ rastreio |
| `servico` | TEXT NULL | `pedidos.servico` | Não | Filtro futuro |
| `status` | TEXT NULL | `pedidos.status` | Exibição | Não entra no cálculo de atraso |
| `nota_fiscal` | TEXT NULL | `notaFiscal.numero` + `/` + `serie` | Sim | Manter formato busca atual |
| `chave_nfe` | TEXT NULL | `notaFiscal.chave` | Não | Extra |
| `valor_total` | NUMERIC NULL | `notaFiscal.valor` | Sim | Já numérico na API |
| `cliente` | TEXT NULL | `clientes.nome` | Sim | |
| `cliente_cnpj` | TEXT NULL | `clientes.cnpj` | Não | Normalizar dígitos |
| `filial_nome` | TEXT NULL | `filiais.nome` | ? | Sample = razão social, não unidade TMB |
| `filial_cnpj` | TEXT NULL | `filiais.cnpj` | Não | |
| `unidade_atual` | TEXT NULL | `unidades.atual` | Não | |
| `unidade_entrega` | TEXT NULL | `unidades.entrega` | **Ver D1** | No sample = "FEDEX BRASIL" |
| `unidade_devolucao` | TEXT NULL | `unidades.devolucao` | Não | |
| `rota` | INT NULL | `unidades.rota` | Não | |
| `filial` | TEXT NULL | **A definir** | Sim (hoje) | Deve equivaler a "Sigla Unidade Entrega" do CSV |
| `cidade_entrega` | TEXT NULL | `destinatarios.cidade` | Sim | |
| `uf_entrega` | TEXT NULL | `destinatarios.uf` | Sim | |
| `destinatario_nome` | TEXT NULL | `destinatarios.nome` | Não | |
| `qtde_volumes` | NUMERIC NULL | `produto.volumes` | Sim | |
| `qtde_itens` | NUMERIC NULL | `produto.itens` | Não | |
| `peso_informado` | NUMERIC NULL | `peso.informado` | Sim (detalhe) | |
| `peso_medio` | NUMERIC NULL | `peso.medio` | Não | Nome API: "medio" |
| `peso_taxado` | NUMERIC NULL | **ausente** | Detalhe | Lacuna vs CSV |
| `dt_prazo_original` | TIMESTAMPTZ NULL | `prazo.original` | Não | |
| `dt_prazo_atual` | TIMESTAMPTZ NULL | `prazo.atual` | Sim | Input do atraso |
| `dt_agendamento` | TIMESTAMPTZ NULL | `atendimento.agendamento` | Sim | Input do atraso |
| `dt_entrega` | TIMESTAMPTZ NULL | `recebedor.data` **ou** campo explícito | Sim | Confirmar semântica |
| `dt_recebimento` | TIMESTAMPTZ NULL | `recebimento.data` | Não | ≠ entrega |
| `dt_cadastro` | TIMESTAMPTZ NULL | `cadastro.data` | Filtro sync | Query usa dataCadastro* |
| `dt_cancelamento` | TIMESTAMPTZ NULL | `cancelamento.data` | Sim | Exclui do atraso |
| `motivo_cancelamento` | TEXT NULL | `cancelamento.motivo` | Não | |
| `motivo_atraso` | TEXT NULL | **ausente** | Detalhe | Lacuna vs CSV |
| `nome_recebedor` | TEXT NULL | `recebedor.nome` | Não | |
| `motorista` | TEXT NULL | `romaneio.motorista` | Detalhe | |
| `remetente` | TEXT NULL | `rementente.nome` | Detalhe | Typo no contrato |
| `cidade_remetente` | TEXT NULL | `rementente.cidade` | Detalhe | |
| `uf_remetente` | TEXT NULL | `rementente.uf` | Detalhe | |
| `ocorrencia_ultima` | TEXT NULL | `ocorrencia.ultima` | Não | Enriquecimento |
| `ocorrencia_data` | TIMESTAMPTZ NULL | `ocorrencia.data` | Não | |
| `pendencia_qtde` | INT NULL | `pendencia.quantidade` | Não | |
| `raw_json` | JSONB/TEXT NULL | item completo | Não | Debug / evolução |
| `synced_at` | TIMESTAMPTZ NOT NULL | job | Sim | Última sync |
| `source` | TEXT NOT NULL | `'api'` / `'csv'` | Sim | Fase paralela |

### 3.2 Campos derivados (não persistir da API — calcular no pipeline)

Iguais a `calcular_atraso` em `limpeza.py`:

| Campo | Regra |
|---|---|
| `prazo_considerado` | `max(dt_prazo_atual, dt_agendamento)` |
| `cancelada` | `dt_cancelamento IS NOT NULL` |
| `entregue` | `dt_entrega IS NOT NULL` |
| `atrasado` | elegível e `prazo_considerado < hoje (America/Sao_Paulo)` |
| `dias_atraso` | dias se atrasado, senão 0 |
| `vence_hoje` | elegível e prazo.date = hoje |

Opcional: materializar numa view `vw_entregas_bi` ou recalcular a cada load
do Streamlit (como hoje).

### 3.3 Tabela `sync_runs` (controle do job)

| Coluna | Tipo | Uso |
|---|---|---|
| `id` | PK | |
| `started_at` / `finished_at` | timestamptz | |
| `filtro_inicio` / `filtro_fim` | date | `dataCadastroInicio/Fim` |
| `pages_fetched` | int | |
| `rows_upserted` | int | |
| `http_status` / `api_code` | text/int | |
| `error` | text null | |

---

## 4. Mapeamento CSV → API → coluna local

Foco nas **23 colunas** que o BI usa hoje.

| CSV (hoje) | API | Coluna local | Status |
|---|---|---|---|
| Nro. Entrega | `pedidos.numero` | `nro_entrega` | Transformação (tipo) — **confirmar identidade** |
| Nota Fiscal | `notaFiscal.numero` + `serie` | `nota_fiscal` | Transformação |
| Cliente | `clientes.nome` | `cliente` | OK |
| Sigla Unidade Entrega | `unidades.entrega` ? | `filial` | **Divergente / bloqueador** |
| Cidade Pessoa Visita | `destinatarios.cidade` | `cidade_entrega` | OK |
| UF Pessoa Visita | `destinatarios.uf` | `uf_entrega` | OK |
| Status | `pedidos.status` | `status` | OK (só UI) |
| Valor Total | `notaFiscal.valor` | `valor_total` | Transformação (já number) |
| Qtde Volumes | `produto.volumes` | `qtde_volumes` | OK |
| Dt. Prazo Atual | `prazo.atual` | `dt_prazo_atual` | Transformação (ISO) |
| Dt. Agendamento | `atendimento.agendamento` | `dt_agendamento` | Transformação |
| Dt. Entrega | `recebedor.data` ? | `dt_entrega` | **Divergente / inferência** |
| Dt. Cancelamento | `cancelamento.data` | `dt_cancelamento` | OK |
| Motivo Cancelamento | `cancelamento.motivo` | `motivo_cancelamento` | OK |
| Motivo de Atraso | — | `motivo_atraso` | **Ausente na API** |
| Nome Recebedor | `recebedor.nome` | `nome_recebedor` | OK |
| Dt. Cadastro | `cadastro.data` | `dt_cadastro` | OK |
| Ult. Motorista | `romaneio.motorista` | `motorista` | OK |
| Nome Remetente | `rementente.nome` | `remetente` | OK (typo na API) |
| Cidade Remetente | `rementente.cidade` | `cidade_remetente` | OK |
| UF Remetente | `rementente.uf` | `uf_remetente` | OK |
| Peso Taxado | — | `peso_taxado` | **Ausente na API** |
| Peso Informado | `peso.informado` | `peso_informado` | OK |

---

## 5. Campos divergentes (detalhe crítico)

### 5.1 Bloqueadores / alto impacto

1. **`filial` (Sigla Unidade Entrega)**  
   - CSV: siglas operacionais TMB (`TMB D. DE CAXIAS`, `TMB VIANA`, …).  
   - API sample: `unidades.entrega` = nome de parceiro (`FEDEX BRASIL`).  
   - `filiais.nome` no sample = razão social do cliente (`AGV Logistica`), não unidade TMB.  
   - Impacto: auth por filial + gráfico `resumo_por_filial`.  
   - Contexto alinhado: TMB é a transportadora/cliente do portal; ainda assim
     pode existir **múltiplas unidades internas**. Precisamos do campo certo
     no tenant TMB.

2. **`dt_entrega`**  
   - CSV: coluna explícita.  
   - API: candidato `recebedor.data` (preenchido em status ENTREGUE no sample).  
   - Risco: marcar entregue demais / de menos → distorce `% atraso`.

3. **`nro_entrega` ↔ `pedidos.numero`**  
   - Números do sample (~2M) vs CSV (~25M) sugerem bases/épocas diferentes.  
   - Sem confirmação, dedupe e paridade CSV×API ficam inválidos.

### 5.2 Médio / baixo impacto

| Lacuna | Impacto no dash |
|---|---|
| `Motivo de Atraso` ausente | Detalhe da entrega (warning); KPIs OK |
| `Peso Taxado` ausente | Detalhe usa `peso_informado` |
| Typo `rementente` | Adapter deve ler a chave real |
| Datas ISO vs `dd/mm/yyyy` | Só transformação |
| NF split numero/serie | Concatenar |
| CNPJ sem máscara | Normalizar se for chave |
| `peso.medio` vs “medido” do CSV | Semântica a confirmar |

### 5.3 Só na API (não usados hoje — candidatos a enriquecer)

`pager.*`, `arquivo.numero`, endereço completo destinatário/remetente,
`cubagem.*`, `cte.*`, `recebimento.data`, `devolucao.data`, `pendencia.*`,
`ocorrencia.*`, demais `romaneio.*`, `produto.itens`, `atendimento.realizados`,
`prazo.original`, `unidades.atual/devolucao/rota`.

---

## 6. Dúvidas para o fornecedor / TI (checklist)

### Acesso e operação

1. Como autenticar o endpoint (`Authorization`, API key, usuário/senha)?
2. O host `endpoint.tmselite.com` é homolog, prod ou ambos?
3. Existe allowlist de IP? VPN obrigatória?
4. Qual o `pageSize` máximo suportado? Há rate limit?
5. Erros: além de `code`/`message` no body, quais HTTP status possíveis?
6. Os filtros `idStatus` e `idServico` aceitam quais valores (lista/enum)?
7. `dataCadastroInicio/Fim` é inclusivo? Timezone? Só data ou datetime?
8. Dá para filtrar por **prazo**, **unidade**, **CNPJ cliente** ou só cadastro?
9. Há webhook/incremental, ou só full pull por período?
10. Existe documentação OpenAPI / Postman oficial?

### Semântica (tenant TMB)

11. No tenant TMB, o que vem em `unidades.entrega`, `unidades.atual`, `filiais.nome`?
12. Qual campo corresponde à **Sigla Unidade Entrega** do relatório CSV?
13. `pedidos.numero` é o mesmo **Nro. Entrega** do export CSV?
14. Qual campo é a **data oficial de entrega**? `recebedor.data` serve?
15. Qual a diferença entre `recebimento.data`, `recebedor.data` e ocorrência de entrega?
16. `prazo.atual` e `atendimento.agendamento` podem ser ambos nulos? Com que frequência?
17. Status textuais: lista completa e se mudam de idioma/casing?
18. Existe campo de **motivo de atraso** em outro endpoint?
19. Existe **peso taxado** em outro campo/endpoint?
20. O typo `rementente` é estável no contrato (não renomear sem versionar)?

### Amostra e aceite

21. Fornecer JSON real do tenant TMB (mesmo período de um CSV conhecido).
22. Confirmar se `totalResults` / paginação cobre 100% do filtro sem buracos.
23. SLA de atualização dos dados na API vs o export CSV diário.

---

## 7. Sync job — comportamento sugerido (quando houver acesso)

1. Autenticar.
2. Para a janela `dataCadastroInicio..Fim` (ex.: D-7 → hoje, ou full backfill inicial):
   - Loop `currentPage = 1..pager.totalPages` com `pageSize` acordado.
3. Para cada item de `results[]`: flatten → upsert em `entregas` por `nro_entrega`.
4. Gravar `raw_json`, `synced_at`, `source='api'`.
5. Registrar `sync_runs`.
6. Portal: `carregar_dados_brutos` lê a tabela (ou export materializado),
   mantém `selecionar_colunas` / `calcular_atraso` (adaptando nomes).

Durante a transição: flag `SOURCE=csv|api|ambos` e comparação de KPIs
na mesma amostra (paridade).

---

## 8. Decisões internas ainda abertas

| ID | Tema | Situação |
|---|---|---|
| D1 | Campo de unidade/filial TMB | **Aberto** — tenant TMB ok, falta campo certo |
| D2 | Data de entrega oficial | Aberto |
| D3 | `pedidos.numero` = Nro. Entrega | Aberto |
| D4 | Motivo de atraso | Aberto (aceitável perder no v1?) |
| D5 | Peso taxado | Aberto (aceitável usar informado?) |
| D6 | Go-live CSV∥API | Recomendado paralelo até paridade |

---

## 9. Próximos passos práticos

1. Obter **credenciais** + sample JSON do tenant TMB (mesmo período do CSV).
2. Responder dúvidas da seção 6 (mínimo: 11–15, 1–4).
3. Congelar mapeamento `filial` e `dt_entrega`.
4. Criar schema físico (`entregas` + `sync_runs`) e job de sync.
5. Feature-flag no portal; validar critérios de paridade.
6. Só então desligar o CSV como fonte primária.
7. PRD formal da migração (quando quiserem documentar como feature).

---

## 10. Referências no repositório

- Sample API: `model.json`
- Colunas BI: `limpeza.py` → `COLUNAS_UTEIS`
- Regra de atraso: `limpeza.py` → `calcular_atraso`
- Análise visual: canvas `csv-api-gap-analysis` / `alinhamento-csv-api` (Cursor)
