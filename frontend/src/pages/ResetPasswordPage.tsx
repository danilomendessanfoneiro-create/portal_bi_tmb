import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { resetPassword, resetPasswordStatus } from "../api";
import "./LoginPage.css";

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();
  const [checking, setChecking] = useState(true);
  const [valid, setValid] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setChecking(true);
      try {
        const res = await resetPasswordStatus(token);
        if (cancelled) return;
        setValid(res.valid);
        setStatusMsg(res.detail);
      } catch (err) {
        if (cancelled) return;
        setValid(false);
        setStatusMsg(err instanceof Error ? err.message : "Link inválido");
      } finally {
        if (!cancelled) setChecking(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await resetPassword({
        token,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao redefinir senha");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={(e) => void onSubmit(e)}>
        <div className="login-brand">
          <h1>Nova senha</h1>
          <p>Defina uma senha definitiva para sua conta</p>
        </div>
        {checking && <p>Validando link…</p>}
        {!checking && !valid && (
          <div className="error-banner">
            {statusMsg || "Link inválido"}
            <div style={{ marginTop: "0.75rem" }}>
              <Link to="/forgot-password">Solicitar nova recuperação</Link>
            </div>
          </div>
        )}
        {!checking && valid && (
          <>
            {error && <div className="error-banner">{error}</div>}
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
            <button
              className="btn btn-primary"
              type="submit"
              disabled={submitting}
              style={{ width: "100%" }}
            >
              {submitting ? "Salvando…" : "Salvar nova senha"}
            </button>
          </>
        )}
        <p style={{ marginTop: "1rem", textAlign: "center" }}>
          <Link to="/login">Voltar ao login</Link>
        </p>
      </form>
    </div>
  );
}
