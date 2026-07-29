# API FastAPI — Portal BI TMB

Entrypoint: `app.api.main:app`

```bash
# local (Vite proxy → :8001)
uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8001
```

- Swagger: http://localhost:8001/api/docs
- Health: http://localhost:8001/api/health

## Rotas principais

| Área | Endpoints |
|------|-----------|
| Auth | `POST /api/auth/login`, `GET /api/auth/me` |
| Usuários | `GET\|POST /api/users`, `GET\|PUT\|DELETE /api/users/{id}` — inclui `report_emails` |
| SMTP | `/api/settings/smtp` |
| Destinatários | `/api/settings/recipients` |
| Automações | `/api/settings/schedules` — `display_name`, `frequency`, `weekday`, `day_of_month` |

Reutiliza `AuthService` / `UserService` / services de settings (sem SQL nos routers).
