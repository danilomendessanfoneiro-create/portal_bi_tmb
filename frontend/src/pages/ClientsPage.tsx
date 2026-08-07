import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import {
  createClient,
  deactivateClient,
  listClients,
  updateClient,
} from "../api";
import { useAuth } from "../auth";
import type { Client, ClientFormValues } from "../types";
import { cnpjDigits, formatCnpjMask } from "../utils/cnpj";

const empty: ClientFormValues = {
  name: "",
  cnpj: "",
  emails: "",
  enabled: true,
};

export function ClientsPage() {
  const { user } = useAuth();
  const isAdmin = (user?.profile || "").toLowerCase() === "admin";
  const [items, setItems] = useState<Client[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [includeDisabled, setIncludeDisabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Client | null>(null);
  const [values, setValues] = useState<ClientFormValues>(empty);
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await listClients({
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

  function openEdit(item: Client) {
    setEditing(item);
    setValues({
      name: item.name,
      cnpj: formatCnpjMask(item.cnpj),
      emails: item.emails || "",
      enabled: item.enabled,
    });
    setModalError("");
    setModalOpen(true);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setModalError("");
    const digits = cnpjDigits(values.cnpj);
    if (digits.length !== 14) {
      setModalError("CNPJ deve ter 14 dígitos (formato 00.000.000/0000-00).");
      return;
    }
    setSaving(true);
    try {
      const payload: ClientFormValues = {
        name: values.name.trim(),
        cnpj: digits,
        emails: values.emails,
        enabled: values.enabled,
      };
      if (editing) {
        await updateClient(editing.id, payload);
      } else {
        await createClient(payload);
      }
      setModalOpen(false);
      setEditing(null);
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
      <h1 className="page-title">Clientes</h1>
      <p className="page-sub">Administração · cadastro para relatórios por CNPJ</p>
      <div className="card">
        <div className="toolbar">
          <div className="toolbar-left">
            <input
              type="search"
              placeholder="Buscar nome, CNPJ ou e-mail…"
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
            Novo cliente
          </button>
        </div>
        {error && <div className="error-banner">{error}</div>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>CNPJ</th>
                <th>E-mails</th>
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
                  <td colSpan={5}>Nenhum cliente encontrado.</td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.name}</td>
                    <td>{formatCnpjMask(item.cnpj)}</td>
                    <td>{item.emails || "—"}</td>
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
                                void deactivateClient(item.id).then(load).catch((err) => {
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
        <div className="modal-backdrop" role="presentation" onClick={() => !saving && setModalOpen(false)}>
          <div className="modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <h2>{editing ? "Editar cliente" : "Novo cliente"}</h2>
            {modalError && <div className="error-banner">{modalError}</div>}
            <form onSubmit={onSubmit}>
              <div className="field">
                <label htmlFor="c-name">Nome</label>
                <input
                  id="c-name"
                  required
                  value={values.name}
                  onChange={(e) => setValues((p) => ({ ...p, name: e.target.value }))}
                />
              </div>
              <div className="field">
                <label htmlFor="c-cnpj">CNPJ</label>
                <input
                  id="c-cnpj"
                  required
                  type="text"
                  inputMode="numeric"
                  autoComplete="off"
                  placeholder="00.000.000/0000-00"
                  maxLength={18}
                  value={values.cnpj}
                  onChange={(e) =>
                    setValues((p) => ({ ...p, cnpj: formatCnpjMask(e.target.value) }))
                  }
                />
                <small style={{ color: "var(--muted)" }}>
                  Digite só números — a máscara é aplicada automaticamente.
                </small>
              </div>
              <div className="field">
                <label htmlFor="c-emails">E-mails</label>
                <input
                  id="c-emails"
                  placeholder="opcional, separados por vírgula ou ;"
                  value={values.emails}
                  onChange={(e) => setValues((p) => ({ ...p, emails: e.target.value }))}
                />
                <small style={{ color: "var(--muted)" }}>
                  Múltiplos e-mails separados por vírgula ou ponto-e-vírgula. Deixe vazio se não houver destinatários.
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
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setModalOpen(false)}
                  disabled={saving}
                >
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
