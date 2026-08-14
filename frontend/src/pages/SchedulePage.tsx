import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { getToken } from "../api";

const API_URL = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");
const TMS_JOB = "fetch_tmselite_spreadsheet";
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

async function fetchSchedules(): Promise<Schedule[]> {
  const res = await fetch(`${API_URL}/settings/schedules`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error("Falha ao carregar automações");
  return res.json();
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
  if (item.display_name) return item.display_name;
  if (item.job_id === "report_branch_daily") return "Envio Diário de Relatórios das Filiais";
  if (item.job_id === "report_client_daily") return "Envio Diário de Relatórios dos Clientes";
  if (item.job_id === "report_managerial") return "Relatório Gerencial";
  if (item.job_id === TMS_JOB) return "Coleta da planilha TMS Elite";
  return item.job_id;
}

function AutomationCard({
  item,
  onSaved,
}: {
  item: Schedule;
  onSaved: (s: Schedule) => void;
}) {
  const isTms = item.job_id === TMS_JOB;
  const [time, setTime] = useState(item.local_time);
  const [enabled, setEnabled] = useState(item.enabled);
  const [days, setDays] = useState<number[]>(item.run_weekdays?.length ? item.run_weekdays : DEFAULT_WEEKDAYS);
  const [tmsUrl, setTmsUrl] = useState(item.tms_login_url || "");
  const [tmsUser, setTmsUser] = useState(item.tms_username || "");
  const [tmsPassword, setTmsPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    setTime(item.local_time);
    setEnabled(item.enabled);
    setDays(item.run_weekdays?.length ? item.run_weekdays : DEFAULT_WEEKDAYS);
    setTmsUrl(item.tms_login_url || "");
    setTmsUser(item.tms_username || "");
    setTmsPassword("");
  }, [item]);

  useEffect(() => {
    if (!success) return;
    const timer = window.setTimeout(() => setSuccess(""), 4000);
    return () => window.clearTimeout(timer);
  }, [success]);

  function toggleDay(value: number) {
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
    <div className="card" style={{ maxWidth: isTms ? 640 : 520, marginBottom: "1.25rem" }}>
      <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>{titleFor(item)}</h2>
      {isTms && (
        <p className="page-sub" style={{ marginTop: 0 }}>
          Login no TMS → Total → Ver Entregas → Excel → Download. A planilha entra no
          mesmo fluxo do upload manual. Sem filtros extras.
        </p>
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
            onChange={(e) => setTime(e.target.value)}
          />
        </div>
        <div className="field">
          <label>Timezone</label>
          <input value={item.timezone || "America/Sao_Paulo"} disabled />
        </div>
        <fieldset className="field" style={{ border: "1px solid var(--border, #ddd)", padding: "0.75rem 1rem" }}>
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
              onChange={(e) => setEnabled(e.target.checked)}
              style={{ marginRight: "0.45rem" }}
            />
            Ativo
          </label>
        </div>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? "Salvando…" : "Salvar"}
        </button>
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

  return (
    <div>
      <h1 className="page-title">Automações</h1>
      <p className="page-sub">
        Configurações · horário, dias da semana e status das automações visíveis
      </p>
      {error && <div className="error-banner">{error}</div>}
      {items.map((item) => (
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
