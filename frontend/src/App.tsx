import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { Shell } from "./components/Shell";
import { AccountPage } from "./pages/AccountPage";
import { ApiIntegrationPage } from "./pages/ApiIntegrationPage";
import { ClientsPage } from "./pages/ClientsPage";
import { ForceChangePasswordPage } from "./pages/ForceChangePasswordPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { ImportPage } from "./pages/ImportPage";
import { LoginPage } from "./pages/LoginPage";
import { RecipientsPage } from "./pages/RecipientsPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { SchedulePage } from "./pages/SchedulePage";
import { SettingsPage } from "./pages/SettingsPage";
import { SmtpPage } from "./pages/SmtpPage";
import { UsersPage } from "./pages/UsersPage";
import { VisualizacaoPage } from "./pages/VisualizacaoPage";

function PrivateShell() {
  const { user, loading } = useAuth();
  if (loading) return <div style={{ padding: "2rem" }}>Carregando…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.must_change_password) {
    return <Navigate to="/force-change-password" replace />;
  }
  return <Shell />;
}

function ForceChangeRoute() {
  const { user, loading } = useAuth();
  if (loading) return <div style={{ padding: "2rem" }}>Carregando…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <ForceChangePasswordPage />;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/force-change-password" element={<ForceChangeRoute />} />
        <Route element={<PrivateShell />}>
          <Route index element={<VisualizacaoPage />} />
          <Route path="visualizacao" element={<Navigate to="/" replace />} />
          <Route path="account" element={<AccountPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="imports" element={<ImportPage />} />
          <Route path="clients" element={<ClientsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="settings/smtp" element={<SmtpPage />} />
          <Route path="settings/recipients" element={<RecipientsPage />} />
          <Route path="settings/api-integration" element={<ApiIntegrationPage />} />
          <Route path="settings/schedules" element={<SchedulePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
