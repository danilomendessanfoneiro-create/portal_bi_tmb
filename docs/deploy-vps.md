# Deploy VPS — Portal BI TMB (híbrido)

## Pré-requisitos

- Ubuntu na VPS Hostinger
- PostgreSQL com banco `portal_bi_tmb` e usuário `portal_bi`
- Código em `/opt/portal-bi-tmb`
- Domínio apontando para o IP (para HTTPS)

## 1. Código e venv

```bash
cd /opt/portal-bi-tmb
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edite DATABASE_URL, JWT_SECRET, URLs públicas
```

## 2. Migrations

```bash
source .venv/bin/activate
python database/deploy/run_migrations.py
```

## 3. Frontend admin

```bash
cd /opt/portal-bi-tmb/frontend
npm ci   # ou npm install
# VITE_API_URL=/api  VITE_BI_URL=https://SEU_DOMINIO/bi
npm run build
```

O build fica em `frontend/dist/` (servido pelo nginx em `/admin/`).

## 4. systemd

```bash
sudo cp deploy/systemd/portal-api.service /etc/systemd/system/
sudo cp deploy/systemd/portal-bi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now portal-api portal-bi
sudo systemctl status portal-api portal-bi
```

## 5. nginx

```bash
sudo cp deploy/nginx/portal-bi-tmb.conf /etc/nginx/sites-available/portal-bi-tmb
sudo ln -sf /etc/nginx/sites-available/portal-bi-tmb /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Rotas:

| Path | Destino |
|------|---------|
| `/` → `/admin/` | SPA React |
| `/admin/` | `frontend/dist` |
| `/api/` | uvicorn `:8000` |
| `/bi/` | Streamlit `:8501` (`baseUrlPath=bi`) |

## 6. HTTPS

Com o DNS pronto:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com
```

Atualize `.env` com `https://seu-dominio.com` nas URLs públicas e reinicie os serviços.

## 7. Smoke check

```bash
curl -s http://127.0.0.1:8000/api/health
curl -sI http://127.0.0.1/admin/
curl -sI http://127.0.0.1/bi/
```

Login admin seed (se não alterado): `admin` / `admin123`.

## Local (dev)

```bash
# terminal 1 — API (Vite proxy em frontend/vite.config.ts → :8001)
uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8001

# terminal 2 — BI (base path /bi, alinhado ao nginx/Vite)
streamlit run app.py --server.baseUrlPath bi --server.port 8501

# terminal 3 — admin
cd frontend && npm run dev
# abra http://localhost:5173/admin/  → Visualização embute /bi/?embed=true
```

Worker / automações: ver [`docs/servico-jobs.md`](servico-jobs.md). Visão geral: [`README.md`](../README.md).
