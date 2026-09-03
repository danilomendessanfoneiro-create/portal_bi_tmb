import { useRef, useState, type FormEvent } from "react";
import HCaptcha from "@hcaptcha/react-hcaptcha";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import "./LoginPage.css";

const SITEKEY = (import.meta.env.VITE_HCAPTCHA_SITEKEY as string | undefined)?.trim() || "";

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const [loginName, setLoginName] = useState("");
  const [password, setPassword] = useState("");
  const [captchaToken, setCaptchaToken] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const captchaRef = useRef<HCaptcha>(null);

  if (!loading && user) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (SITEKEY && !captchaToken) {
      setError("Complete o desafio hCaptcha.");
      return;
    }
    setSubmitting(true);
    try {
      await login(loginName.trim(), password, captchaToken || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no login");
      setCaptchaToken("");
      captchaRef.current?.resetCaptcha();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={onSubmit}>
        <div className="login-brand">
          <img
            className="login-logo"
            src={`${import.meta.env.BASE_URL}logos/logo_full.png`}
            alt="TMB Logística"
          />
          <h1>Portal BI</h1>
          <p>Administração — entre com seu usuário</p>
        </div>
        {error && <div className="error-banner">{error}</div>}
        <div className="field">
          <label htmlFor="login">Usuário</label>
          <input
            id="login"
            autoComplete="username"
            value={loginName}
            onChange={(e) => setLoginName(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="password">Senha</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {SITEKEY ? (
          <div className="login-captcha">
            <HCaptcha
              ref={captchaRef}
              sitekey={SITEKEY}
              onVerify={(token) => setCaptchaToken(token)}
              onExpire={() => setCaptchaToken("")}
              onError={() => {
                setCaptchaToken("");
                setError("Falha ao carregar o hCaptcha.");
              }}
            />
          </div>
        ) : null}
        <button className="btn btn-primary" type="submit" disabled={submitting} style={{ width: "100%" }}>
          {submitting ? "Entrando…" : "Entrar"}
        </button>
        <p style={{ marginTop: "1rem", textAlign: "center" }}>
          <Link to="/forgot-password">Esqueci minha senha</Link>
        </p>
      </form>
    </div>
  );
}
