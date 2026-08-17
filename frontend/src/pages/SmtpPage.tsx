import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import {
  createSmtp,
  deactivateSmtp,
  listSmtp,
  updateSmtp,
} from "../api";
import { useAuth } from "../auth";
import type { SmtpFormValues, SmtpSettings } from "../types";

const empty: SmtpFormValues = {
  name: "",
  host: "",
  port: 587,
  username: "",
  password: "",
  use_tls: true,
  sender_email: "",
  sender_name: "",
  timeout_seconds: "30",
  is_default: false,
  enabled: true,
};

export function SmtpPage() {
  const { user } = useAuth();
  const isAdmin = (user?.profile || "").toLowerCase() === "admin";
  const [items, setItems] = useState<SmtpSettings[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [includeDisabled, setIncludeDisabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<SmtpSettings | null>(null);
  const [values, setValues] = useState<SmtpFormValues>(empty);
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await listSmtp({
        search: search || undefined,
        page,
        page_size: 10,
        include_disabled: includeDisabled,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao listar");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (isAdmin) void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, page, search, includeDisabled]);

  if (!isAdmin) return <Navigate to="/" replace />;

  function openCreate() {
    setEditing(null);
    setValues(empty);
    setModalError("");
    setModalOpen(true);
  }

  function openEdit(item: SmtpSettings) {
    setEditing(item);
    setValues({
      name: item.name,
      host: item.host,
      port: item.port,
      username: item.username,
      password: "",
      use_tls: item.use_tls,
      sender_email: item.sender_email,
      sender_name: item.sender_name,
      timeout_seconds: item.timeout_seconds != null ? String(item.timeout_seconds) : "",
      is_default: item.is_default,
      enabled: item.enabled,
    });
    setModalError("");
    setModalOpen(true);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setModalError("");
    try {
      if (editing) {
        await updateSmtp(editing.id, values);
      } else {
        await createSmtp(values);
      }
      setModalOpen(false);
      await load();
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / 10));

  return (
    <div>
      <h1 className="page-title">SMTP</h1>
      <p className="page-sub">Configurações · servidor de e-mail para relatórios</p>
      <div className="card">
        <div className="toolbar">
          <div className="toolbar-left">
            <input
              type="search"
              placeholder="Buscar nome, host…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  setPage(1);
                  setSearch(searchInput.trim());
                }
              }}
            />
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                setPage(1);
                setSearch(searchInput.trim());
              }}
            >
              Buscar
            </button>
            <label style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
              <input
                type="checkbox"
                checked={includeDisabled}
                onChange={(e) => {
                  setIncludeDisabled(e.target.checked);
                  setPage(1);
                }}
                style={{ marginRight: "0.35rem" }}
              />
              Incluir desativados
            </label>
          </div>
          <button type="button" className="btn btn-primary" onClick={openCreate}>
            Nova configuração
          </button>
        </div>
        {error && <div className="error-banner">{error}</div>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Host</th>
                <th>Remetente</th>
                <th>Padrão</th>
                <th>Status</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6}>Carregando…</td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={6}>Nenhuma configuração encontrada.</td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>
                      {item.host}:{item.port}
                    </td>
                    <td>{item.sender_email}</td>
                    <td>{item.is_default ? "Sim" : "Não"}</td>
                    <td>
                      <span className={`badge ${item.enabled ? "badge-on" : "badge-off"}`}>
                        {item.enabled ? "Ativo" : "Inativo"}
                      </span>
                    </td>
                    <td>
                      <div className="row-actions">
                        <button type="button" className="btn btn-ghost" onClick={() => openEdit(item)}>
                          Editar
                        </button>
                        {item.enabled && (
                          <button
                            type="button"
                            className="btn btn-danger"
                            onClick={() => {
                              if (window.confirm(`Desativar "${item.name}"?`)) {
                                void deactivateSmtp(item.id).then(load).catch((err) => {
                                  setError(err instanceof Error ? err.message : "Erro");
                                });
                              }
                            }}
                          >
                            Desativar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="pagination">
          <span>
            {total} registro(s) · página {page}/{totalPages}
          </span>
          <button type="button" className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Anterior
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Próxima
          </button>
        </div>
      </div>

      {modalOpen && (
        <div className="modal-backdrop" role="presentation" onClick={() => setModalOpen(false)}>
          <div className="modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <h2>{editing ? "Editar SMTP" : "Nova configuração SMTP"}</h2>
            {modalError && <div className="error-banner">{modalError}</div>}
            <form onSubmit={onSubmit}>
              {(
                [
                  ["name", "Nome", "text"],
                  ["host", "Host", "text"],
                  ["port", "Porta", "number"],
                  ["username", "Usuário", "text"],
                  ["password", editing ? "Senha (opcional)" : "Senha", "password"],
                  ["sender_email", "Remetente (e-mail)", "email"],
                  ["sender_name", "Nome do remetente", "text"],
                  ["timeout_seconds", "Timeout (segundos)", "number"],
                ] as const
              ).map(([key, label, type]) => (
                <div className="field" key={key}>
                  <label htmlFor={`smtp-${key}`}>{label}</label>
                  <input
                    id={`smtp-${key}`}
                    type={type}
                    value={String(values[key])}
                    required={key !== "timeout_seconds" && !(editing && key === "password")}
                    onChange={(e) =>
                      setValues((prev) => ({
                        ...prev,
                        [key]: type === "number" && key === "port" ? Number(e.target.value) : e.target.value,
                      }))
                    }
                  />
                </div>
              ))}
              <div className="field">
                <label>
                  <input
                    type="checkbox"
                    checked={values.use_tls}
                    onChange={(e) => setValues((p) => ({ ...p, use_tls: e.target.checked }))}
                    style={{ marginRight: "0.45rem" }}
                  />
                  SSL/TLS
                </label>
                <p className="page-sub" style={{ margin: "0.35rem 0 0", fontSize: "0.85rem" }}>
                  Porta 465 usa SSL implícito automaticamente. Porta 587 usa STARTTLS quando esta opção estiver marcada.
                </p>
              </div>
              <div className="field">
                <label>
                  <input
                    type="checkbox"
                    checked={values.is_default}
                    onChange={(e) => setValues((p) => ({ ...p, is_default: e.target.checked }))}
                    style={{ marginRight: "0.45rem" }}
                  />
                  Configuração padrão
                </label>
              </div>
              <div className="field">
                <label>
                  <input
                    type="checkbox"
                    checked={values.enabled}
                    onChange={(e) => setValues((p) => ({ ...p, enabled: e.target.checked }))}
                    style={{ marginRight: "0.45rem" }}
                  />
                  Ativo
                </label>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setModalOpen(false)} disabled={saving}>
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
