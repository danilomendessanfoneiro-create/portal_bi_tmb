import { useMemo } from "react";
import { biEmbedUrl, getToken } from "../api";
import "./VisualizacaoPage.css";

export function VisualizacaoPage() {
  const token = getToken() ?? "";
  const src = useMemo(() => (token ? biEmbedUrl() : ""), [token]);

  if (!token) {
    return (
      <div className="bi-embed bi-embed-wait">
        Preparando visualização…
      </div>
    );
  }

  return (
    <div className="bi-embed">
      <iframe
        key={token}
        title="Visualização — Portal BI de Entregas"
        src={src}
        className="bi-iframe"
        allow="fullscreen"
      />
    </div>
  );
}
