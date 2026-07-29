import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { getToken } from "../api";

const API_URL = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

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
}

const WEEKDAYS = [
  { value: 0, label: "Domingo" },
  { value: 1, label: "Segunda-feira" },
  { value: 2, label: "Terça-feira" },
  { value: 3, label: "Quarta-feira" },
  { value: 4, label: "Quinta-feira" },
  { value: 5, label: "Sexta-feira" },
  { value: 6, label: "Sábado" },
];

async function fetchSchedules(): Promise<Schedule[]> {
  const res = await fetch(`${API_URL}/settings/schedules`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error("Falha ao carregar automações");
  return res.json();
}

async function updateSchedule(jobId: string, body: Partial<Schedule>): Promise<Schedule> {
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
    throw new Error(err.detail || "Falha ao salvar");
  }
  return res.json();
}

function AutomationCard({
  item,
  onSaved,
}: {
  item: Schedule;
  onSaved: (s: Schedule) => void;
}) {
  const isBranch = item.job_id === "report_branch_daily";
  const [time, setTime] = useState(item.local_time);
  const [enabled, setEnabled] = useState(item.enabled);
  const [frequency, setFrequency] = useState(item.frequency || "daily");
  const [weekday, setWeekday] = useState(item.weekday ?? 1);
  const [dayOfMonth, setDayOfMonth] = useState(item.day_of_month ?? 1);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setTime(item.local_time);
    setEnabled(item.enabled);
    setFrequency(item.frequency || "daily");
    setWeekday(item.weekday ?? 1);
    setDayOfMonth(item.day_of_month ?? 1);
  }, [item]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const body: Partial<Schedule> = {
        local_time: time,
        enabled,
        frequency: isBranch ? "daily" : frequency,
      };
      if (!isBranch && frequency === "weekly") body.weekday = weekday;
      if (!isBranch && frequency === "monthly") body.day_of_month = dayOfMonth;
      const updated = await updateSchedule(item.job_id, body);
      onSaved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  const title =
    item.display_name ||
    (isBranch ? "Envio Diário de Relatórios das Filiais" : "Relatório Gerencial");

  return (
    <div className="card" style={{ maxWidth: 520, marginBottom: "1.25rem" }}>
      <h2 style={{ marginTop: 0, fontSize: "1.1rem" }}>{title}</h2>
      {error && <div className="error-banner">{error}</div>}
      <form onSubmit={onSubmit}>
        {!isBranch && (
          <div className="field">
            <label htmlFor={`freq-${item.id}`}>Periodicidade</label>
            <select
              id={`freq-${item.id}`}
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
            >
              <option value="daily">Diário</option>
              <option value="weekly">Semanal</option>
              <option value="monthly">Mensal</option>
            </select>
          </div>
        )}
        {!isBranch && frequency === "weekly" && (
          <div className="field">
            <label htmlFor={`wd-${item.id}`}>Dia da semana</label>
            <select
              id={`wd-${item.id}`}
              value={weekday}
              onChange={(e) => setWeekday(Number(e.target.value))}
            >
              {WEEKDAYS.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </select>
          </div>
        )}
        {!isBranch && frequency === "monthly" && (
          <div className="field">
            <label htmlFor={`dom-${item.id}`}>Dia do mês</label>
            <input
              id={`dom-${item.id}`}
              type="number"
              min={1}
              max={31}
              required
              value={dayOfMonth}
              onChange={(e) => setDayOfMonth(Number(e.target.value))}
            />
          </div>
        )}
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
        Configurações · horários de envio dos relatórios das filiais e gerencial
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
        O timer da VPS chama o worker com <code>--if-due</code>; cada automação é avaliada
        independentemente. Semanal/mensal do gerencial: apenas parametrização nesta etapa.
      </p>
    </div>
  );
}
