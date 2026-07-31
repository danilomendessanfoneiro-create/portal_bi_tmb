import { useCallback, useEffect, useRef, useState, type DragEvent } from "react";
import { Navigate } from "react-router-dom";
import {
  dispatchImportReportEmails,
  getActiveDataset,
  getImportBatch,
  listImportBatches,
  softDeleteImportBatch,
  startImportBatch,
  uploadImportFile,
  validateImportBatch,
  type ActiveDataset,
  type ImportBatch,
} from "../api";
import { useAuth } from "../auth";

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(ms?: number | null): string {
  if (!ms && ms !== 0) return "—";
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    uploaded: "Enviado",
    validating: "Validando",
    validated_ok: "Validado",
    validated_error: "Com erros",
    importing: "Importando",
    imported: "Importado",
    failed: "Falhou",
  };
  return map[status] || status;
}

function needsFreshUpload(status?: string | null): boolean {
  return !status || ["imported", "failed", "validated_error"].includes(status);
}

export function ImportPage() {
  const { user } = useAuth();
  const isAdmin = (user?.profile || "").toLowerCase() === "admin";
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [batch, setBatch] = useState<ImportBatch | null>(null);
  const [history, setHistory] = useState<ImportBatch[]>([]);
  const [histTotal, setHistTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [dispatchMsg, setDispatchMsg] = useState("");
  const [activeDataset, setActiveDataset] = useState<ActiveDataset | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<number | null>(null);

  const clearFileSelection = useCallback(() => {
    setFile(null);
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  const loadActiveDataset = useCallback(async () => {
    try {
      setActiveDataset(await getActiveDataset());
    } catch {
      setActiveDataset(null);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const data = await listImportBatches({
        search: search || undefined,
        status: statusFilter || undefined,
        created_by: userFilter || undefined,
        date_from: dateFrom ? `${dateFrom}T00:00:00` : undefined,
        date_to: dateTo ? `${dateTo}T23:59:59` : undefined,
        page: 1,
        page_size: 20,
      });
      setHistory(data.items);
      setHistTotal(data.total);
      await loadActiveDataset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar histórico");
    }
  }, [search, statusFilter, userFilter, dateFrom, dateTo, loadActiveDataset]);

  useEffect(() => {
    if (isAdmin) void loadHistory();
  }, [isAdmin, loadHistory]);

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  if (!isAdmin) return <Navigate to="/" replace />;

  function pickFile(f: File | null) {
    setError("");
    if (!f) {
      setFile(null);
      return;
    }
    const ext = f.name.toLowerCase();
    if (!ext.endsWith(".csv") && !ext.endsWith(".xlsx") && !ext.endsWith(".xls")) {
      setError("Formato inválido. Use .csv, .xlsx ou .xls.");
      setFile(null);
      return;
    }
    setFile(f);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0] || null;
    pickFile(f);
  }

  async function onValidate() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      let current = batch;
      if (needsFreshUpload(current?.status)) {
        current = await uploadImportFile(file);
        setBatch(current);
      }
      if (!current) {
        throw new Error("Falha ao preparar o lote para validação.");
      }
      const validated = await validateImportBatch(current.id);
      setBatch(validated);
      if (validated.status === "validated_error") {
        clearFileSelection();
      }
      await loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha na validação");
    } finally {
      setBusy(false);
    }
  }

  function startPolling(id: number) {
    if (pollRef.current) window.clearInterval(pollRef.current);
    pollRef.current = window.setInterval(async () => {
      try {
        const b = await getImportBatch(id);
        setBatch(b);
        if (b.status === "imported" || b.status === "failed") {
          if (pollRef.current) window.clearInterval(pollRef.current);
          pollRef.current = null;
          setBusy(false);
          clearFileSelection();
          await loadHistory();
        }
      } catch {
        /* ignore transient */
      }
    }, 800);
  }

  async function onImport() {
    if (!batch || batch.status !== "validated_ok") return;
    setBusy(true);
    setError("");
    try {
      const started = await startImportBatch(batch.id);
      setBatch(started);
      startPolling(started.id);
    } catch (err) {
      setBusy(false);
      setError(err instanceof Error ? err.message : "Falha na importação");
    }
  }

  async function onSoftDelete(id: number) {
    if (!window.confirm("Excluir logicamente este registro do histórico?")) return;
    setError("");
    try {
      await softDeleteImportBatch(id);
      if (batch?.id === id) {
        setBatch(null);
        clearFileSelection();
      }
      await loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha na exclusão lógica");
    }
  }

  async function onDispatchEmails() {
    if (
      !window.confirm(
        "Disparar agora o envio dos e-mails de relatório (filiais + gerencial)?",
      )
    ) {
      return;
    }
    setDispatching(true);
    setDispatchMsg("");
    setError("");
    try {
      const res = await dispatchImportReportEmails();
      setDispatchMsg(res.detail || "Envio de e-mails disparado em background.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao disparar e-mails");
    } finally {
      setDispatching(false);
    }
  }

  const canImport = batch?.status === "validated_ok" && !busy;
  const importing = batch?.status === "importing";
  const canValidate = !!file && !busy && !importing;

  return (
    <div>
      <h1 className="page-title">Importação de Dados</h1>
      <p className="page-sub">Upload e validação de planilha para atualizar entregas do Portal BI</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          style={{
            border: `2px dashed ${dragOver ? "var(--orange, #F6A532)" : "#CBD5E1"}`,
            borderRadius: 12,
            padding: "1.75rem",
            textAlign: "center",
            background: dragOver ? "#FFF8EE" : "#F8FAFC",
            marginBottom: "1rem",
          }}
        >
          <p style={{ margin: "0 0 0.75rem", color: "var(--muted)" }}>
            Arraste a planilha aqui ou selecione no computador
          </p>
          <button type="button" className="btn btn-ghost" onClick={() => inputRef.current?.click()}>
            Selecionar arquivo
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            hidden
            onChange={(e) => pickFile(e.target.files?.[0] || null)}
          />
        </div>

        {file && (
          <div style={{ marginBottom: "1rem", fontSize: "0.9rem" }}>
            <div>
              <strong>{file.name}</strong>
            </div>
            <div style={{ color: "var(--muted)" }}>
              {formatBytes(file.size)}
              {file.lastModified
                ? ` · alterado em ${new Date(file.lastModified).toLocaleString("pt-BR")}`
                : ""}
            </div>
          </div>
        )}

        {!file && batch && (batch.status === "validated_error" || batch.status === "failed") && (
          <p style={{ color: "var(--muted)", fontSize: "0.9rem", marginBottom: "1rem" }}>
            Arquivo removido do cache. Envie novamente a planilha para uma nova tentativa.
          </p>
        )}

        {!file && batch?.status === "imported" && (
          <p style={{ color: "var(--muted)", fontSize: "0.9rem", marginBottom: "1rem" }}>
            Importação concluída. Para outra importação, envie uma nova planilha.
          </p>
        )}

        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button type="button" className="btn btn-primary" disabled={!canValidate} onClick={onValidate}>
            {busy && !importing ? "Validando…" : "Validar planilha"}
          </button>
          <button type="button" className="btn btn-primary" disabled={!canImport} onClick={onImport}>
            {importing ? "Importando…" : "Importar dados"}
          </button>
        </div>

        {batch && (
          <div style={{ marginTop: "1.25rem" }}>
            <p style={{ margin: "0 0 0.5rem" }}>
              Status: <strong>{statusLabel(batch.status)}</strong>
              {batch.total_rows > 0 && (
                <>
                  {" "}
                  · {batch.total_rows} registros · {batch.valid_rows} válidos · {batch.error_rows} com
                  erro
                </>
              )}
            </p>

            {(importing || batch.status === "imported") && (
              <div style={{ marginBottom: "0.75rem" }}>
                <div
                  style={{
                    height: 10,
                    background: "#E2E8F0",
                    borderRadius: 999,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${Math.min(100, batch.progress_pct || 0)}%`,
                      height: "100%",
                      background: "#1E8A5F",
                      transition: "width 0.3s",
                    }}
                  />
                </div>
                <div style={{ fontSize: "0.85rem", color: "var(--muted)", marginTop: 6 }}>
                  {batch.rows_processed} processados
                  {batch.total_rows
                    ? ` · ${Math.max(0, batch.total_rows - batch.rows_processed)} restantes`
                    : ""}
                  {` · ${batch.progress_pct?.toFixed?.(0) ?? batch.progress_pct}%`}
                </div>
              </div>
            )}

            {batch.status === "imported" && (
              <div
                style={{
                  background: "#E8F6F0",
                  border: "1px solid #B7E4D0",
                  borderRadius: 10,
                  padding: "0.75rem 1rem",
                  marginBottom: "0.75rem",
                }}
              >
                Importação concluída. {batch.rows_processed} processados. {batch.rows_updated}{" "}
                atualizados. {batch.rows_inserted} inseridos. Tempo:{" "}
                {formatDuration(batch.duration_ms)}.
              </div>
            )}

            {batch.validation_errors?.length > 0 && (
              <div>
                <strong>Erros de validação</strong>
                <ul style={{ maxHeight: 220, overflow: "auto", marginTop: 8 }}>
                  {batch.validation_errors.map((e, i) => (
                    <li key={`${e.row_number}-${i}`}>{e.message}</li>
                  ))}
                </ul>
              </div>
            )}
            {batch.error_message && batch.status === "failed" && (
              <div className="error-banner">{batch.error_message}</div>
            )}
          </div>
        )}
      </div>

      <div className="card">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "0.75rem",
            flexWrap: "wrap",
            marginBottom: "0.75rem",
          }}
        >
          <h2 style={{ margin: 0, fontSize: "1.05rem" }}>Histórico de importações</h2>
          <button
            type="button"
            className="btn btn-primary"
            disabled={dispatching || busy}
            onClick={() => void onDispatchEmails()}
          >
            {dispatching ? "Disparando…" : "Disparar Envio de E-mails"}
          </button>
        </div>
        {activeDataset && activeDataset.source !== "empty" && (
          <div
            style={{
              background: "#EEF2FF",
              border: "1px solid #C7D2FE",
              borderRadius: 10,
              padding: "0.65rem 0.85rem",
              marginBottom: "0.75rem",
              fontSize: "0.9rem",
            }}
          >
            Lote ativo:{" "}
            <strong>
              {activeDataset.source === "manual_import" ? "Planilha" : "API"}
            </strong>
            {" — "}
            {activeDataset.label}
            {activeDataset.row_count != null ? ` · ${activeDataset.row_count} entregas` : ""}
          </div>
        )}
        {dispatchMsg && (
          <div
            style={{
              background: "#E8F6F0",
              border: "1px solid #B7E4D0",
              borderRadius: 10,
              padding: "0.65rem 0.9rem",
              marginBottom: "0.75rem",
              fontSize: "0.9rem",
            }}
          >
            {dispatchMsg}
          </div>
        )}
        <div className="toolbar" style={{ marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <input
            type="search"
            placeholder="Arquivo…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void loadHistory();
            }}
          />
          <input
            type="search"
            placeholder="Usuário…"
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void loadHistory();
            }}
          />
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} title="Data de" />
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} title="Data até" />
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">Todos os status</option>
            <option value="imported">Importado</option>
            <option value="validated_error">Com erros</option>
            <option value="failed">Falhou</option>
            <option value="importing">Importando</option>
          </select>
          <button type="button" className="btn btn-ghost" onClick={() => void loadHistory()}>
            Filtrar
          </button>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Data/Hora</th>
                <th>Usuário</th>
                <th>Arquivo</th>
                <th>Total</th>
                <th>Inseridos</th>
                <th>Atualizados</th>
                <th>Erros</th>
                <th>Tempo</th>
                <th>Status</th>
                <th>Lote</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan={11}>Nenhuma importação registrada.</td>
                </tr>
              ) : (
                history.map((h) => (
                  <tr key={h.id}>
                    <td>{h.created_on ? new Date(h.created_on).toLocaleString("pt-BR") : "—"}</td>
                    <td>{h.created_by || "—"}</td>
                    <td>{h.file_name}</td>
                    <td>{h.total_rows}</td>
                    <td>{h.rows_inserted}</td>
                    <td>{h.rows_updated}</td>
                    <td>{h.error_rows}</td>
                    <td>{formatDuration(h.duration_ms)}</td>
                    <td>{statusLabel(h.status)}</td>
                    <td>
                      {activeDataset?.source === "manual_import" &&
                      activeDataset.batch_id === h.id ? (
                        <span className="badge badge-on">Ativo</span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      {(h.status === "validated_error" || h.status === "failed") && (
                        <button
                          type="button"
                          className="btn btn-ghost"
                          style={{ fontSize: "0.8rem", padding: "0.25rem 0.5rem" }}
                          onClick={() => void onSoftDelete(h.id)}
                        >
                          Excluir
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>{histTotal} registro(s)</p>
      </div>
    </div>
  );
}
