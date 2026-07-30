import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { getToken } from "../api";

const API_URL = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

interface ApiSettings {
  id: number;
  name: string;
  base_url: string;
  endpoint: string;
  timeout_seconds: number;
  page_size: number;
  initial_load_days: number;
  is_default: boolean;
  enabled: boolean;
  has_token: boolean;
}

interface FormValues {
  name: string;
  base_url: string;
  endpoint: string;
  token: string;
  timeout_seconds: string;
  page_size: string;
  initial_load_days: string;
  is_default: boolean;
  enabled: boolean;
}

const empty: FormValues = {
  name: "",
  base_url: "https://app.tmselite.com",
  endpoint: "/api/v1/entregas/relatorios/geral",
  token: "",
  timeout_seconds: "60",
  page_size: "500",
  initial_load_days: "20",
  is_default: true,
  enabled: true,
};

async function listItems(): Promise<{ items: ApiSettings[]; total: number }> {
  const res = await fetch(`${API_URL}/settings/api-integration?include_disabled=true`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error("Falha ao carregar configurações");
  return res.json();
}

async function createItem(body: Record<string, unknown>): Promise<ApiSettings> {
  const res = await fetch(`${API_URL}/settings/api-integration`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getToken()}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Falha ao criar");
  }
  return res.json();
}

async function updateItem(id: number, body: Record<string, unknown>): Promise<ApiSettings> {
  const res = await fetch(`${API_URL}/settings/api-integration/${id}`, {
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

async function deactivateItem(id: number): Promise<void> {
  const res = await fetch(`${API_URL}/settings/api-integration/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error("Falha ao desativar");
}

export function ApiIntegrationPage() {
  const { user } = useAuth();
  const isAdmin = (user?.profile || "").toLowerCase() === "admin";
  const [items, setItems] = useState<ApiSettings[]>([]);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ApiSettings | null>(null);
  const [values, setValues] = useState<FormValues>(empty);
  const [saving, setSaving] = useState(false);

  async function load() {
    setError("");
    try {
      const data = await listItems();
      setItems(data.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    }
  }

  useEffect(() => {
    if (isAdmin) void load();
  }, [isAdmin]);

  if (!isAdmin) return <Navigate to="/" replace />;

  function openCreate() {
    setEditing(null);
    setValues(empty);
    setModalOpen(true);
  }

  function openEdit(item: ApiSettings) {
    setEditing(item);
    setValues({
      name: item.name,
      base_url: item.base_url,
      endpoint: item.endpoint,
      token: "",
      timeout_seconds: String(item.timeout_seconds),
      page_size: String(item.page_size),
      initial_load_days: String(item.initial_load_days),
      is_default: item.is_default,
      enabled: item.enabled,
    });
    setModalOpen(true);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const body: Record<string, unknown> = {
        name: values.name,
        base_url: values.base_url,
        endpoint: values.endpoint,
        timeout_seconds: Number(values.timeout_seconds),
        page_size: Number(values.page_size),
        initial_load_days: Number(values.initial_load_days),
        is_default: values.is_default,
        enabled: values.enabled,
      };
      if (editing) {
        if (values.token.trim()) body.token = values.token.trim();
        await updateItem(editing.id, body);
      } else {
        body.token = values.token.trim();
        await createItem(body);
      }
      setModalOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h1 className="page-title">Integração API</h1>
      <p className="page-sub">Configurações · TMS Elite (URL, token, paginação)</p>
      {error && <div className="error-banner">{error}</div>}
      <div style={{ marginBottom: "1rem" }}>
        <button type="button" className="btn btn-primary" onClick={openCreate}>
          Nova configuração
        </button>
      </div>
      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Base URL</th>
              <th>Endpoint</th>
              <th>Padrão</th>
              <th>Ativo</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.name}</td>
                <td>{item.base_url}</td>
                <td>{item.endpoint}</td>
                <td>{item.is_default ? "Sim" : "Não"}</td>
                <td>{item.enabled ? "Sim" : "Não"}</td>
                <td>
                  <button type="button" className="btn btn-ghost" onClick={() => openEdit(item)}>
                    Editar
                  </button>
                  {item.enabled && (
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={() => void deactivateItem(item.id).then(load)}
                    >
                      Desativar
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modalOpen && (
        <div className="modal-backdrop" onClick={() => setModalOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{editing ? "Editar integração" : "Nova integração"}</h2>
            <form onSubmit={onSubmit}>
              <div className="field">
                <label>Nome</label>
                <input
                  required
                  value={values.name}
                  onChange={(e) => setValues({ ...values, name: e.target.value })}
                />
              </div>
              <div className="field">
                <label>URL base</label>
                <input
                  required
                  value={values.base_url}
                  onChange={(e) => setValues({ ...values, base_url: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Endpoint</label>
                <input
                  required
                  value={values.endpoint}
                  onChange={(e) => setValues({ ...values, endpoint: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Bearer token {editing ? "(deixe vazio para manter)" : ""}</label>
                <input
                  type="password"
                  required={!editing}
                  value={values.token}
                  onChange={(e) => setValues({ ...values, token: e.target.value })}
                  placeholder="somente o token, sem a palavra Bearer"
                  autoComplete="new-password"
                />
              </div>
              <div className="field">
                <label>Timeout (s)</label>
                <input
                  type="number"
                  required
                  value={values.timeout_seconds}
                  onChange={(e) => setValues({ ...values, timeout_seconds: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Registros por página</label>
                <input
                  type="number"
                  required
                  value={values.page_size}
                  onChange={(e) => setValues({ ...values, page_size: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Dias carga inicial</label>
                <input
                  type="number"
                  required
                  value={values.initial_load_days}
                  onChange={(e) => setValues({ ...values, initial_load_days: e.target.value })}
                />
              </div>
              <div className="field">
                <label>
                  <input
                    type="checkbox"
                    checked={values.is_default}
                    onChange={(e) => setValues({ ...values, is_default: e.target.checked })}
                  />{" "}
                  Padrão
                </label>
              </div>
              <div className="field">
                <label>
                  <input
                    type="checkbox"
                    checked={values.enabled}
                    onChange={(e) => setValues({ ...values, enabled: e.target.checked })}
                  />{" "}
                  Ativo
                </label>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setModalOpen(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? "Salvando…" : "Salvar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
