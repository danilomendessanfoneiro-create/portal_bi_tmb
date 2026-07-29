import { useEffect, useState, type FormEvent } from "react";
import type { User, UserFormValues } from "../types";

interface Props {
  open: boolean;
  title: string;
  initial?: Partial<UserFormValues> | null;
  requirePassword: boolean;
  saving: boolean;
  error: string;
  onClose: () => void;
  onSubmit: (values: UserFormValues) => Promise<void>;
}

const empty: UserFormValues = {
  login: "",
  password: "",
  profile: "filial",
  branch: "",
  display_name: "",
  name: "",
  code: "",
  report_emails: "",
  enabled: true,
};

export function UserModal({
  open,
  title,
  initial,
  requirePassword,
  saving,
  error,
  onClose,
  onSubmit,
}: Props) {
  const [values, setValues] = useState<UserFormValues>(empty);

  useEffect(() => {
    if (open) {
      setValues({ ...empty, ...initial });
    }
  }, [open, initial]);

  if (!open) return null;

  function set<K extends keyof UserFormValues>(key: K, value: UserFormValues[K]) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await onSubmit(values);
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <h2>{title}</h2>
        {error && <div className="error-banner">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="u-login">Login</label>
            <input
              id="u-login"
              value={values.login}
              onChange={(e) => set("login", e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="u-password">
              Senha {requirePassword ? "" : "(opcional)"}
            </label>
            <input
              id="u-password"
              type="password"
              value={values.password}
              onChange={(e) => set("password", e.target.value)}
              required={requirePassword}
              autoComplete="new-password"
            />
          </div>
          <div className="field">
            <label htmlFor="u-profile">Perfil</label>
            <select
              id="u-profile"
              value={values.profile}
              onChange={(e) => set("profile", e.target.value)}
            >
              <option value="admin">admin</option>
              <option value="filial">filial</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="u-branch">Filial</label>
            <input
              id="u-branch"
              value={values.branch}
              onChange={(e) => set("branch", e.target.value)}
              required={values.profile === "filial"}
            />
          </div>
          <div className="field">
            <label htmlFor="u-display">Nome de exibição</label>
            <input
              id="u-display"
              value={values.display_name}
              onChange={(e) => set("display_name", e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="u-name">Nome</label>
            <input
              id="u-name"
              value={values.name}
              onChange={(e) => set("name", e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="u-code">Código</label>
            <input
              id="u-code"
              value={values.code}
              onChange={(e) => set("code", e.target.value)}
            />
          </div>
          {values.profile === "filial" && (
            <div className="field">
              <label htmlFor="u-emails">E-mails do relatório</label>
              <textarea
                id="u-emails"
                rows={3}
                value={values.report_emails}
                onChange={(e) => set("report_emails", e.target.value)}
                placeholder="financeiro@empresa.com.br; gerente@empresa.com.br"
              />
              <small style={{ color: "var(--muted)" }}>
                Separe múltiplos e-mails com ponto e vírgula (;).
              </small>
            </div>
          )}
          <div className="field">
            <label htmlFor="u-enabled">
              <input
                id="u-enabled"
                type="checkbox"
                checked={values.enabled}
                onChange={(e) => set("enabled", e.target.checked)}
                style={{ marginRight: "0.45rem" }}
              />
              Ativo
            </label>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Salvando…" : "Salvar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function userToForm(user: User): UserFormValues {
  return {
    login: user.login,
    password: "",
    profile: user.profile,
    branch: user.branch || "",
    display_name: user.display_name || "",
    name: user.name || "",
    code: user.code || "",
    report_emails: user.report_emails || "",
    enabled: user.enabled,
  };
}
