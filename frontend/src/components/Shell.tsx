import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth";
import "./Shell.css";

export function Shell() {
  const { user, logout } = useAuth();
  const isAdmin = (user?.profile || "").toLowerCase() === "admin";

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <img
            className="brand-logo"
            src={`${import.meta.env.BASE_URL}logos/logo.png`}
            alt="TMB"
          />
          <div>
            <strong>Portal BI</strong>
            <small>TMB Logística</small>
          </div>
        </div>

        <nav className="nav">
          <div className="nav-group">Meu</div>
          <NavLink
            to="/"
            end
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            Visualização
          </NavLink>

          {isAdmin && (
            <>
              <div className="nav-group">Administração</div>
              <NavLink to="/users" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
                Usuários
              </NavLink>
              <NavLink
                to="/imports"
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              >
                Importação de Dados
              </NavLink>
              <div className="nav-group">Configurações</div>
              <NavLink
                to="/settings/smtp"
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              >
                SMTP
              </NavLink>
              <NavLink
                to="/settings/recipients"
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              >
                Destinatários de E-mail
              </NavLink>
              <NavLink
                to="/settings/api-integration"
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              >
                Integração API
              </NavLink>
              <NavLink
                to="/settings/schedules"
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              >
                Automações
              </NavLink>
              <NavLink
                to="/settings"
                end
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              >
                Visão geral
              </NavLink>
            </>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="user-chip">
            <strong>{user?.display_name || user?.login}</strong>
            <span>{user?.profile}</span>
          </div>
          <button type="button" className="btn btn-ghost" onClick={logout}>
            Sair
          </button>
        </div>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
