import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { createUser, deactivateUser, listUsers, updateUser } from "../api";
import { useAuth } from "../auth";
import { UserModal, userToForm } from "../components/UserModal";
import type { User, UserFormValues } from "../types";

export function UsersPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [sortBy, setSortBy] = useState("login");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [includeDisabled, setIncludeDisabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [saving, setSaving] = useState(false);
  const [modalError, setModalError] = useState("");

  const isAdmin = (user?.profile || "").toLowerCase() === "admin";

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listUsers({
        search: search || undefined,
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_dir: sortDir,
        include_disabled: includeDisabled,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao listar");
    } finally {
      setLoading(false);
    }
  }, [search, page, pageSize, sortBy, sortDir, includeDisabled]);

  useEffect(() => {
    if (isAdmin) void load();
  }, [load, isAdmin]);

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  function toggleSort(col: string) {
    if (sortBy === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(col);
      setSortDir("asc");
    }
  }

  function openCreate() {
    setEditing(null);
    setModalError("");
    setModalOpen(true);
  }

  function openEdit(u: User) {
    setEditing(u);
    setModalError("");
    setModalOpen(true);
  }

  async function handleSave(values: UserFormValues) {
    setSaving(true);
    setModalError("");
    try {
      if (editing) {
        await updateUser(editing.id, values);
      } else {
        await createUser(values);
      }
      setModalOpen(false);
      await load();
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(u: User) {
    if (!window.confirm(`Desativar o usuário "${u.login}"?`)) return;
    try {
      await deactivateUser(u.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao desativar");
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div>
      <h1 className="page-title">Usuários</h1>
      <p className="page-sub">Gerencie acessos ao portal (PostgreSQL · prb_users)</p>

      <div className="card">
        <div className="toolbar">
          <div className="toolbar-left">
            <input
              type="search"
              placeholder="Buscar login, nome…"
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
            Novo usuário
          </button>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {[
                  ["login", "Login"],
                  ["display_name", "Nome"],
                  ["profile", "Perfil"],
                  ["branch", "Filial"],
                  ["enabled", "Status"],
                ].map(([col, label]) => (
                  <th key={col} onClick={() => toggleSort(col)}>
                    {label}
                    {sortBy === col ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
                  </th>
                ))}
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
                  <td colSpan={6}>Nenhum usuário encontrado.</td>
                </tr>
              ) : (
                items.map((u) => (
                  <tr key={u.id}>
                    <td>{u.login}</td>
                    <td>{u.display_name || u.name || "—"}</td>
                    <td>
                      <span className={`badge badge-${u.profile === "admin" ? "admin" : "filial"}`}>
                        {u.profile}
                      </span>
                    </td>
                    <td>{u.branch || "—"}</td>
                    <td>
                      <span className={`badge ${u.enabled ? "badge-on" : "badge-off"}`}>
                        {u.enabled ? "Ativo" : "Inativo"}
                      </span>
                    </td>
                    <td>
                      <div className="row-actions">
                        <button type="button" className="btn btn-ghost" onClick={() => openEdit(u)}>
                          Editar
                        </button>
                        {u.enabled && (
                          <button
                            type="button"
                            className="btn btn-danger"
                            onClick={() => void handleDeactivate(u)}
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
          <button
            type="button"
            className="btn btn-ghost"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
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

      <UserModal
        open={modalOpen}
        title={editing ? "Editar usuário" : "Novo usuário"}
        initial={editing ? userToForm(editing) : null}
        requirePassword={!editing}
        saving={saving}
        error={modalError}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSave}
      />
    </div>
  );
}
