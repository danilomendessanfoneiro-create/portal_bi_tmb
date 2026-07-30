import { Navigate, NavLink } from "react-router-dom";
import { useAuth } from "../auth";

export function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = (user?.profile || "").toLowerCase() === "admin";

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return (
    <div>
      <h1 className="page-title">Configurações</h1>
      <p className="page-sub">Administração · parametrizações do portal</p>
      <div className="card" style={{ display: "grid", gap: "0.85rem" }}>
        <NavLink to="/settings/smtp" className="nav-link" style={{ color: "var(--navy)" }}>
          SMTP — servidor de e-mail
        </NavLink>
        <NavLink to="/settings/recipients" className="nav-link" style={{ color: "var(--navy)" }}>
          Destinatários de E-mail — relatórios automáticos
        </NavLink>
        <NavLink to="/settings/api-integration" className="nav-link" style={{ color: "var(--navy)" }}>
          Integração API — TMS Elite
        </NavLink>
        <NavLink to="/settings/schedules" className="nav-link" style={{ color: "var(--navy)" }}>
          Automações — horários dos relatórios e importações
        </NavLink>
      </div>
    </div>
  );
}
