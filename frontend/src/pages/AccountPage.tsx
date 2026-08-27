import { useState, type FormEvent } from "react";
import { changeOwnPassword } from "../api";
import { useAuth } from "../auth";

export function AccountPage() {
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setOk("");
    setSaving(true);
    try {
      await changeOwnPassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setOk("Senha alterada com sucesso.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao alterar senha");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h1 className="page-title">Minha conta</h1>
      <p className="page-sub">
        {user?.display_name || user?.login}
        {user?.login_email ? ` · ${user.login_email}` : ""}
      </p>

      <div className="card" style={{ maxWidth: 480 }}>
        <h2 style={{ marginTop: 0, fontSize: "1.05rem" }}>Alterar senha</h2>
        {error && <div className="error-banner">{error}</div>}
        {ok && (
          <div className="error-banner" style={{ background: "#e8f5e9", color: "#1b5e20" }}>
            {ok}
          </div>
        )}
        <form onSubmit={(e) => void handleSubmit(e)}>
          <div className="field">
            <label htmlFor="cur">Senha atual</label>
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
            <label htmlFor="npw">Nova senha</label>
            <input
              id="npw"
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
            <label htmlFor="cpw">Confirmar nova senha</label>
            <input
              id="cpw"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              autoComplete="new-password"
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Salvando…" : "Salvar"}
          </button>
        </form>
      </div>
    </div>
  );
}
