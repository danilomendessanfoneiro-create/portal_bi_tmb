-- 034_create_prb_progress_snapshot_item.sql
-- Itens do snapshot de Progressão (lote completo do upload; chave = nro_entrega).

CREATE TABLE IF NOT EXISTS prb_progress_snapshot_item (
    id                  BIGSERIAL PRIMARY KEY,
    snapshot_run_id     INTEGER NOT NULL REFERENCES prb_progress_snapshot_run (id) ON DELETE CASCADE,
    nro_entrega         VARCHAR(100) NOT NULL,
    remessa_numero      VARCHAR(100),
    status              VARCHAR(100) NOT NULL,
    filial              VARCHAR(200),
    cliente             VARCHAR(500),
    cnpj_cliente        VARCHAR(14),
    cidade_entrega      VARCHAR(200),
    uf_entrega          VARCHAR(10),
    motorista           VARCHAR(300),
    valor_total         NUMERIC(18, 2),
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_progress_item_run_nro UNIQUE (snapshot_run_id, nro_entrega)
);

CREATE INDEX IF NOT EXISTS ix_prb_progress_snapshot_item_run
    ON prb_progress_snapshot_item (snapshot_run_id);

CREATE INDEX IF NOT EXISTS ix_prb_progress_snapshot_item_nro
    ON prb_progress_snapshot_item (nro_entrega);

CREATE INDEX IF NOT EXISTS ix_prb_progress_snapshot_item_cnpj
    ON prb_progress_snapshot_item (cnpj_cliente)
    WHERE cnpj_cliente IS NOT NULL AND enabled = TRUE;

CREATE INDEX IF NOT EXISTS ix_prb_progress_snapshot_item_filial
    ON prb_progress_snapshot_item (filial);

CREATE INDEX IF NOT EXISTS ix_prb_progress_snapshot_item_status
    ON prb_progress_snapshot_item (status);
