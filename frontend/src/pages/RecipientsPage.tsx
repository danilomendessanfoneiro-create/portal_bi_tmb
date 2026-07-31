import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import {
  createRecipient,
  deactivateRecipient,
  listRecipients,
  updateRecipient,
} from "../api";
import { useAuth } from "../auth";
import type { EmailRecipient, RecipientFormValues } from "../types";

const empty: RecipientFormValues = {
  name: "",
  email: "",
  role_title: "",
  department: "",
  receive_daily: true,
  receive_weekly: false,
  receive_monthly: false,
  enabled: true,
};

export function RecipientsPage() {
  const { user } = useAuth();
  const isAdmin = (user?.profile || "").toLowerCase() === "admin";
  const [items, setItems] = useState<EmailRecipient[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [includeDisabled, setIncludeDisabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<EmailRecipient | null>(null);
  const [values, setValues] = useState<RecipientFormValues>(empty);
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await listRecipients({
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

  function openEdit(item: EmailRecipient) {
    setEditing(item);
    setValues({
      name: item.name,
      email: item.email,
      role_title: item.role_title || "",
      department: item.department || "",
      receive_daily: true,
      receive_weekly: false,
      receive_monthly: false,
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
      const payload: RecipientFormValues = {
        ...values,
        receive_daily: true,
        receive_weekly: false,
        receive_monthly: false,
      };
      if (editing) {
        await updateRecipient(editing.id, payload);
      } else {
        await createRecipient(payload);
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
      <h1 className="page-title">Destinatários de E-mail</h1>
      <p className="page-sub">Configurações · quem recebe os relatórios automáticos</p>
      <div className="card">
        <div className="toolbar">
          <div className="toolbar-left">
            <input
              type="search"
              placeholder="Buscar nome ou e-mail…"
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
            Novo destinatário
          </button>
        </div>
        {error && <div className="error-banner">{error}</div>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>E-mail</th>
                <th>Tipo de relatório</th>
                <th>Status</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5}>Carregando…</td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={5}>Nenhum destinatário encontrado.</td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>{item.email}</td>
                    <td>Diário</td>
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
                              if (window.confirm(`Desativar "${item.email}"?`)) {
                                void deactivateRecipient(item.id).then(load).catch((err) => {
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
            <h2>{editing ? "Editar destinatário" : "Novo destinatário"}</h2>
            {modalError && <div className="error-banner">{modalError}</div>}
            <form onSubmit={onSubmit}>
              <div className="field">
                <label htmlFor="r-name">Nome</label>
                <input
                  id="r-name"
                  required
                  value={values.name}
                  onChange={(e) => setValues((p) => ({ ...p, name: e.target.value }))}
                />
              </div>
              <div className="field">
                <label htmlFor="r-email">E-mail</label>
                <input
                  id="r-email"
                  type="email"
                  required
                  value={values.email}
                  onChange={(e) => setValues((p) => ({ ...p, email: e.target.value }))}
                />
              </div>
              <div className="field">
                <label htmlFor="r-role">Cargo</label>
                <input
                  id="r-role"
                  value={values.role_title}
                  onChange={(e) => setValues((p) => ({ ...p, role_title: e.target.value }))}
                />
              </div>
              <div className="field">
                <label htmlFor="r-dept">Departamento</label>
                <input
                  id="r-dept"
                  value={values.department}
                  onChange={(e) => setValues((p) => ({ ...p, department: e.target.value }))}
                />
              </div>
              <div className="field">
                <label>Tipo de relatório</label>
                <input value="Diário" disabled />
                <small style={{ color: "var(--muted)" }}>
                  Definido automaticamente pelo sistema (semanal/mensal não estão disponíveis).
                </small>
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
