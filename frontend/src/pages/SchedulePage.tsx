import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { getToken } from "../api";

const API_URL = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");
const TMS_JOB = "fetch_tmselite_spreadsheet";
const API_JOBS = new Set(["import_deliveries_daily", "import_deliveries_initial"]);
const DEFAULT_WEEKDAYS = [1, 2, 3, 4, 5, 6];
const WEEKDAY_OPTIONS: { value: number; label: string }[] = [
  { value: 1, label: "Segunda-feira" },
  { value: 2, label: "Terça-feira" },
  { value: 3, label: "Quarta-feira" },
  { value: 4, label: "Quinta-feira" },
  { value: 5, label: "Sexta-feira" },
  { value: 6, label: "Sábado" },
  { value: 0, label: "Domingo" },
];

interface Schedule {
  id: number;
  job_id: string;
  display_name?: string | null;
  local_time: string;
  timezone: string;
  frequency: string;
  weekday?: number | null;
  day_of_month?: number | null;
  enabled: boolean;
  tms_login_url?: string | null;
  tms_username?: string | null;
  has_tms_password?: boolean;
  run_weekdays?: number[];
}

interface ApiSettingsRow {
  id: number;
  name: string;
  base_url: string;
  endpoint: string;
  is_default: boolean;
  enabled: boolean;
  has_token: boolean;
}

async function fetchSchedules(): Promise<Schedule[]> {
  const res = await fetch(`${API_URL}/settings/schedules`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error("Falha ao carregar automações");
  return res.json();
}

async function fetchApiSettings(): Promise<ApiSettingsRow[]> {
  const res = await fetch(`${API_URL}/settings/api-integration?include_disabled=true`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error("Falha ao carregar configuração da API");
  const data = await res.json();
  return data.items || [];
}

async function updateSchedule(jobId: string, body: Record<string, unknown>): Promise<Schedule> {
  const res = await fetch(`${API_URL}/settings/schedules/${jobId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${getToken()}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg || String(d)).join("; ")
          : "Falha ao salvar";
    throw new Error(message || "Falha ao salvar");
  }
  return res.json();
}

function titleFor(item: Schedule): string {
  if (item.job_id === TMS_JOB) return item.display_name || "Importação de pedidos";
  if (item.display_name) return item.display_name;
  if (item.job_id === "report_branch_daily") return "Envio Diário de Relatórios das Filiais";
  if (item.job_id === "report_client_daily") return "Envio Diário de Relatórios dos Clientes";
  if (item.job_id === "report_managerial") return "Relatório Gerencial";
  if (item.job_id === "import_deliveries_daily") return "Atualização Diária (API Entregas)";
  if (item.job_id === "import_deliveries_initial") return "Migração Inicial (API Entregas)";
  return item.job_id;
}

function ApiConfigSnippet() {
  const [items, setItems] = useState<ApiSettingsRow[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void fetchApiSettings()
      .then(setItems)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, []);

  return (
    <div className="card" style={{ maxWidth: 640, marginBottom: "1.25rem" }}>
      <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>Configuração da API</h2>
      <p className="page-sub" style={{ marginTop: 0 }}>
        Credenciais da integração TMS Elite (URL/token). Os jobs de API abaixo
        permanecem <strong>desabilitados</strong> — a importação ativa é por planilha
        (Importação de pedidos).
      </p>
      {error && <div className="error-banner">{error}</div>}
      {items.length === 0 && !error ? (
        <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
          Nenhuma configuração cadastrada.
        </p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Base URL</th>
                <th>Endpoint</th>
                <th>Token</th>
                <th>Ativo</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    {item.name}
                    {item.is_default ? " (padrão)" : ""}
                  </td>
                  <td>{item.base_url}</td>
                  <td>{item.endpoint}</td>
                  <td>{item.has_token ? "••••••••" : "—"}</td>
                  <td>{item.enabled ? "Sim" : "Não"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p style={{ marginTop: "0.85rem", marginBottom: 0 }}>
        <Link to="/settings/api-integration">Abrir configuração completa da API →</Link>
      </p>
    </div>
  );
}

function AutomationCard({
  item,
  onSaved,
}: {
  item: Schedule;
  onSaved: (s: Schedule) => void;
}) {
  const isTms = item.job_id === TMS_JOB;
  const isApiJob = API_JOBS.has(item.job_id);
  const [time, setTime] = useState(item.local_time);
  const [enabled, setEnabled] = useState(isApiJob ? false : item.enabled);
  const [days, setDays] = useState<number[]>(item.run_weekdays?.length ? item.run_weekdays : DEFAULT_WEEKDAYS);
  const [tmsUrl, setTmsUrl] = useState(item.tms_login_url || "");
  const [tmsUser, setTmsUser] = useState(item.tms_username || "");
  const [tmsPassword, setTmsPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    setTime(item.local_time);
    setEnabled(isApiJob ? false : item.enabled);
    setDays(item.run_weekdays?.length ? item.run_weekdays : DEFAULT_WEEKDAYS);
    setTmsUrl(item.tms_login_url || "");
    setTmsUser(item.tms_username || "");
    setTmsPassword("");
  }, [item, isApiJob]);

  useEffect(() => {
    if (!success) return;
    const timer = window.setTimeout(() => setSuccess(""), 4000);
    return () => window.clearTimeout(timer);
  }, [success]);

  function toggleDay(value: number) {
    if (isApiJob) return;
    setSuccess("");
    setDays((prev) => {
      if (prev.includes(value)) {
        const next = prev.filter((d) => d !== value);
        return next.length ? next : prev;
      }
      return [...prev, value].sort((a, b) => a - b);
    });
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (isApiJob) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const body: Record<string, unknown> = {
        local_time: time,
        enabled,
        frequency: "daily",
        run_weekdays: days,
      };
      if (isTms) {
        body.tms_login_url = tmsUrl;
        body.tms_username = tmsUser;
        if (tmsPassword.trim()) body.tms_password = tmsPassword;
      }
      const updated = await updateSchedule(item.job_id, body);
      setTmsPassword("");
      setSuccess("Automação salva com sucesso.");
      onSaved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card" style={{ maxWidth: isTms || isApiJob ? 640 : 520, marginBottom: "1.25rem" }}>
      <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>{titleFor(item)}</h2>
      {isApiJob && (
        <div className="error-banner" style={{ background: "#f3f5f9", color: "var(--navy)" }}>
          Job da API <strong>desabilitado</strong>. A importação em produção usa{" "}
          <strong>Importação de pedidos</strong> (planilha). Credenciais da API ficam na
          seção acima, só para referência/configuração.
        </div>
      )}
      {error && <div className="error-banner">{error}</div>}
      {success && <div className="success-banner">{success}</div>}
      <form onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor={`time-${item.id}`}>Horário local (HH:MM)</label>
          <input
            id={`time-${item.id}`}
            type="time"
            required
            value={time}
            disabled={isApiJob}
            onChange={(e) => setTime(e.target.value)}
          />
        </div>
        <div className="field">
          <label>Timezone</label>
          <input value={item.timezone || "America/Sao_Paulo"} disabled />
        </div>
        <fieldset
          className="field"
          disabled={isApiJob}
          style={{ border: "1px solid var(--border, #ddd)", padding: "0.75rem 1rem" }}
        >
          <legend>Dias de execução</legend>
          {WEEKDAY_OPTIONS.map((opt) => (
            <label key={opt.value} style={{ display: "block", marginBottom: "0.35rem" }}>
              <input
                type="checkbox"
                checked={days.includes(opt.value)}
                onChange={() => toggleDay(opt.value)}
                style={{ marginRight: "0.45rem" }}
              />
              {opt.label}
            </label>
          ))}
        </fieldset>
        {isTms && (
          <>
            <div className="field">
              <label htmlFor={`tms-url-${item.id}`}>URL de login do TMS</label>
              <input
                id={`tms-url-${item.id}`}
                type="url"
                required={enabled}
                value={tmsUrl}
                onChange={(e) => setTmsUrl(e.target.value)}
                placeholder="https://tmblogistica.tmselite.com/login"
              />
            </div>
            <div className="field">
              <label htmlFor={`tms-user-${item.id}`}>Usuário TMS</label>
              <input
                id={`tms-user-${item.id}`}
                autoComplete="username"
                required={enabled}
                value={tmsUser}
                onChange={(e) => setTmsUser(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor={`tms-pass-${item.id}`}>Senha TMS</label>
              <input
                id={`tms-pass-${item.id}`}
                type="password"
                autoComplete="new-password"
                value={tmsPassword}
                onChange={(e) => setTmsPassword(e.target.value)}
                placeholder={item.has_tms_password ? "•••••••• (preencha para alterar)" : ""}
              />
            </div>
          </>
        )}
        <div className="field">
          <label>
            <input
              type="checkbox"
              checked={enabled}
              disabled={isApiJob}
              onChange={(e) => setEnabled(e.target.checked)}
              style={{ marginRight: "0.45rem" }}
            />
            Ativo{isApiJob ? " (bloqueado)" : ""}
          </label>
        </div>
        {!isApiJob && (
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Salvando…" : "Salvar"}
          </button>
        )}
      </form>
    </div>
  );
}

export function SchedulePage() {
  const { user } = useAuth();
  const isAdmin = (user?.profile || "").toLowerCase() === "admin";
  const [items, setItems] = useState<Schedule[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isAdmin) return;
    void fetchSchedules()
      .then(setItems)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, [isAdmin]);

  if (!isAdmin) return <Navigate to="/" replace />;

  const tmsItems = items.filter((i) => i.job_id === TMS_JOB);
  const apiItems = items.filter((i) => API_JOBS.has(i.job_id));
  const reportItems = items.filter((i) => i.job_id !== TMS_JOB && !API_JOBS.has(i.job_id));

  return (
    <div>
      <h1 className="page-title">Automações</h1>
      <p className="page-sub">
        Configurações · horário, dias da semana e status das automações
      </p>
      {error && <div className="error-banner">{error}</div>}
      {tmsItems.map((item) => (
        <AutomationCard
          key={item.job_id}
          item={item}
          onSaved={(updated) =>
            setItems((prev) => prev.map((s) => (s.job_id === updated.job_id ? updated : s)))
          }
        />
      ))}
      <ApiConfigSnippet />
      {apiItems.map((item) => (
        <AutomationCard
          key={item.job_id}
          item={item}
          onSaved={(updated) =>
            setItems((prev) => prev.map((s) => (s.job_id === updated.job_id ? updated : s)))
          }
        />
      ))}
      {reportItems.map((item) => (
        <AutomationCard
          key={item.job_id}
          item={item}
          onSaved={(updated) =>
            setItems((prev) => prev.map((s) => (s.job_id === updated.job_id ? updated : s)))
          }
        />
      ))}
      <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
        Cada automação segue o próprio horário e os dias configurados.
      </p>
    </div>
  );
}
