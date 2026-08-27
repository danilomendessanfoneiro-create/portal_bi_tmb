import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../api";
import "./LoginPage.css";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    setSubmitting(true);
    try {
      const res = await forgotPassword(email.trim());
      setMessage(res.detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao solicitar recuperação");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={(e) => void onSubmit(e)}>
        <div className="login-brand">
          <h1>Recuperar senha</h1>
          <p>Informe o e-mail de login cadastrado</p>
        </div>
        {error && <div className="error-banner">{error}</div>}
        {message && (
          <div className="error-banner" style={{ background: "#e8f5e9", color: "#1b5e20" }}>
            {message}
          </div>
        )}
        <div className="field">
          <label htmlFor="email">E-mail</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={submitting} style={{ width: "100%" }}>
          {submitting ? "Enviando…" : "Solicitar recuperação"}
        </button>
        <p style={{ marginTop: "1rem", textAlign: "center" }}>
          <Link to="/login">Voltar ao login</Link>
        </p>
      </form>
    </div>
  );
}
