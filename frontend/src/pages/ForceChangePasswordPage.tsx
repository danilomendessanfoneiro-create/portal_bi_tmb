import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { changeOwnPassword } from "../api";
import { useAuth } from "../auth";

/**
 * Mandatory password change after provisional login.
 * Uses current provisional password + new definitive password.
 */
export function ForceChangePasswordPage() {
  const { user, logout, refresh } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (!user.must_change_password) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await changeOwnPassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao definir senha");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={(e) => void handleSubmit(e)}>
        <div className="login-brand">
          <h1>Definir senha definitiva</h1>
          <p>No primeiro acesso é obrigatório trocar a senha provisória.</p>
        </div>
        {error && <div className="error-banner">{error}</div>}
        <div className="field">
          <label htmlFor="cur">Senha provisória atual</label>
          <input
            id="cur"
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
        <div className="field">
          <label htmlFor="np">Nova senha</label>
          <input
            id="np"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
          <small style={{ color: "var(--muted)" }}>
            Mínimo 12 caracteres, com maiúscula, minúscula, número e caractere especial.
          </small>
        </div>
        <div className="field">
          <label htmlFor="cp">Confirmar nova senha</label>
          <input
            id="cp"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={saving} style={{ width: "100%" }}>
          {saving ? "Salvando…" : "Salvar e continuar"}
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          style={{ width: "100%", marginTop: "0.5rem" }}
          onClick={logout}
        >
          Sair
        </button>
      </form>
    </div>
  );
}
