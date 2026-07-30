# Integração API TMS Elite → Persistência local (BI TMB)

Status: **implementado** (branch atual). Fonte operacional do BI: `prb_deliveries`.
CSV **não** é mais a fonte do dashboard/jobs de relatório.

## Endpoint

```
GET {base_url}{endpoint}
  ?dataCadastroInicio=YYYY-MM-DD
  &dataCadastroFim=YYYY-MM-DD
  &currentPage=1
  &pageSize=500
Authorization: Bearer <token>
```

Configuração exclusiva via **Admin → Configurações → Integração API** (`prb_api_settings`).
Token criptografado (mesmo padrão SMTP). Apenas uma config padrão ativa.

## Camada

```
app/integrations/tmselite/
  client.py   # HTTP + paginação
  mapper.py   # JSON → DeliveryRecord (chave: remessa.numero)
  service.py  # fetch + map
  models.py
  exceptions.py
```

## Jobs

```bash
python -m worker run import_deliveries_initial --dry-run
python -m worker run import_deliveries_daily --force
python -m worker run import_deliveries   # alias da daily
```

- **Inicial** (`import_deliveries_initial`): janela `hoje - initial_load_days` → hoje (seed Automações 03:00, default disabled).
- **Diária** (`import_deliveries_daily`): `dataCadastro` do dia (seed 07:00).
- Logs: `prb_integration_logs`.

## Migrations

`014`–`019` (`prb_api_settings`, `prb_deliveries`, `prb_integration_logs` + audits + seeds).

## Chave e mapeamento

- Unique: `remessa.numero` → `remessa_numero` / `nro_entrega`
- Filial: `unidadeEntrega.sigla` (fallback `unidadeAtual.sigla` / `embarcador.nomeFilial`)
- Referência estrutural de desenvolvimento: `model.json`

## Open points

Filtros extras (status, data entrega) preparados no client (`idStatus` / `idServico`), aguardando contrato do fornecedor.
