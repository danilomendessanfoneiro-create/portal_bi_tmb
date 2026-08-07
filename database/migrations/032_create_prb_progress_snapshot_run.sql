-- 032_create_prb_progress_snapshot_run.sql
-- Snapshot de Progressão: 1 run por import_batch_id (somente manual_import nesta entrega).

CREATE TABLE IF NOT EXISTS prb_progress_snapshot_run (
    id                  SERIAL PRIMARY KEY,
    import_batch_id     INTEGER NOT NULL REFERENCES prb_import_batches (id),
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source              VARCHAR(40) NOT NULL DEFAULT 'manual_import',
    row_count           INTEGER NOT NULL DEFAULT 0,
    rule_version        VARCHAR(40),
    notes               TEXT,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_progress_run_batch UNIQUE (import_batch_id),
    CONSTRAINT ck_prb_progress_snapshot_run_source CHECK (source IN ('manual_import'))
);

CREATE INDEX IF NOT EXISTS ix_prb_progress_snapshot_run_captured_at
    ON prb_progress_snapshot_run (captured_at DESC);
