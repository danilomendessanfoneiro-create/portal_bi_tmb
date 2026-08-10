# Clientes (`prb_clients`)

Cadastro admin de clientes (Nome, CNPJ, e-mails) para relatórios por CNPJ.

## Migrations

- `database/migrations/037_create_prb_clients.sql`
- `database/migrations/038_create_prb_clients_audit.sql`

## API (admin)

- `GET|POST /api/settings/clients`
- `PUT|DELETE /api/settings/clients/{id}`

## Carga inicial a partir do CSV

Lê `dados/entregas_relatorio.csv` (colunas `CNPJ Cliente` e `Cliente`), upserta por CNPJ normalizado e deixa e-mails vazios na inserção. Idempotente.

```bash
.\.venv\Scripts\python.exe database/deploy/seed_clients_from_csv.py
.\.venv\Scripts\python.exe database/deploy/seed_clients_from_csv.py --dry-run
```

No deploy VPS (opcional):

```bash
./deploy/update.sh --seed-clients
# ou só o seed:
python database/deploy/seed_clients_from_csv.py --csv dados/entregas_relatorio.csv
```
