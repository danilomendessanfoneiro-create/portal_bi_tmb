import { useEffect, useState, type FormEvent } from "react";

interface Props {
  open: boolean;
  loginLabel: string;
  saving: boolean;
  error: string;
  generatedPassword: string | null;
  onClose: () => void;
  onSubmit: (payload: { password?: string; generate: boolean }) => Promise<void>;
}

export function ChangePasswordModal({
  open,
  loginLabel,
  saving,
  error,
  generatedPassword,
  onClose,
  onSubmit,
}: Props) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [localError, setLocalError] = useState("");

  useEffect(() => {
    if (open) {
      setPassword("");
      setConfirm("");
      setLocalError("");
    }
  }, [open]);

  if (!open) return null;

  async function handleManual(e: FormEvent) {
    e.preventDefault();
    setLocalError("");
    if (password !== confirm) {
      setLocalError("A confirmação não confere com a nova senha.");
      return;
    }
    await onSubmit({ password, generate: false });
  }

  async function handleGenerate() {
    setLocalError("");
    await onSubmit({ generate: true });
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <h2>Alterar senha</h2>
        <p className="page-sub" style={{ marginTop: 0 }}>
          Usuário: <strong>{loginLabel}</strong>
        </p>
        {(error || localError) && (
          <div className="error-banner">{error || localError}</div>
        )}
        {generatedPassword && (
          <div className="error-banner" style={{ background: "#e8f5e9", color: "#1b5e20" }}>
            Senha gerada (copie agora; não será exibida novamente):{" "}
            <code>{generatedPassword}</code>
          </div>
        )}
        <form onSubmit={(e) => void handleManual(e)}>
          <div className="field">
            <label htmlFor="cp-password">Nova senha</label>
            <input
              id="cp-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="cp-confirm">Confirmar nova senha</label>
            <input
              id="cp-confirm"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              required
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>
              Fechar
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => void handleGenerate()}
              disabled={saving}
            >
              Gerar senha segura
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
