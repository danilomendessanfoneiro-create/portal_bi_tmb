import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth";
import "./Shell.css";

export function Shell() {
  const { user, logout } = useAuth();
  const isAdmin = (user?.profile || "").toLowerCase() === "admin";
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const isVisualizacao =
    location.pathname === "/" || location.pathname === "" || location.pathname === "/visualizacao";

  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDrawerOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawerOpen]);

  const shellClass = [
    "shell",
    isVisualizacao ? "shell-bi" : "",
    drawerOpen ? "drawer-open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={shellClass}>
      <header className="topbar">
        <button
          type="button"
          className="menu-toggle"
          aria-label={drawerOpen ? "Fechar menu" : "Abrir menu"}
          aria-expanded={drawerOpen}
          onClick={() => setDrawerOpen((v) => !v)}
        >
          <span className="menu-toggle-bars" aria-hidden />
        </button>
        <div className="topbar-title">
          {isVisualizacao ? "Visualização" : "Portal BI"}
        </div>
      </header>

      <div
        className="drawer-backdrop"
        aria-hidden={!drawerOpen}
        onClick={() => setDrawerOpen(false)}
      />

      <aside className="sidebar" id="app-sidebar">
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
            onClick={() => setDrawerOpen(false)}
          >
            Visualização
          </NavLink>

          {isAdmin && (
            <>
              <div className="nav-group">Administração</div>
              <NavLink
                to="/users"
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
                onClick={() => setDrawerOpen(false)}
              >
                Usuários
              </NavLink>
              <NavLink
                to="/imports"
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
                onClick={() => setDrawerOpen(false)}
              >
                Importação de Dados
              </NavLink>
              <NavLink
                to="/clients"
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
                onClick={() => setDrawerOpen(false)}
              >
                Clientes
              </NavLink>
              <div className="nav-group">Configurações</div>
              <NavLink
                to="/settings/smtp"
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
                onClick={() => setDrawerOpen(false)}
              >
                SMTP
              </NavLink>
              <NavLink
                to="/settings/recipients"
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
                onClick={() => setDrawerOpen(false)}
              >
                Destinatários de E-mail
              </NavLink>
              <NavLink
                to="/settings/api-integration"
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
                onClick={() => setDrawerOpen(false)}
              >
                Integração API
              </NavLink>
              <NavLink
                to="/settings/schedules"
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
                onClick={() => setDrawerOpen(false)}
              >
                Automações
              </NavLink>
              <NavLink
                to="/settings"
                end
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
                onClick={() => setDrawerOpen(false)}
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
