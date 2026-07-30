-- 018_create_prb_integration_logs.sql

CREATE TABLE IF NOT EXISTS prb_integration_logs (
    id                  SERIAL PRIMARY KEY,
    job_id              VARCHAR(100) NOT NULL,
    business_date       DATE,
    status              VARCHAR(20) NOT NULL,
    started_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    finished_on         TIMESTAMP WITHOUT TIME ZONE,
    duration_ms         INTEGER,
    pages_processed     INTEGER NOT NULL DEFAULT 0,
    rows_inserted       INTEGER NOT NULL DEFAULT 0,
    rows_updated        INTEGER NOT NULL DEFAULT 0,
    error_count         INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT,
    filter_start        DATE,
    filter_end          DATE,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT ck_prb_integration_logs_status CHECK (status IN ('running', 'success', 'failed', 'partial'))
);

CREATE INDEX IF NOT EXISTS ix_prb_integration_logs_job ON prb_integration_logs (job_id, started_on DESC);
CREATE INDEX IF NOT EXISTS ix_prb_integration_logs_status ON prb_integration_logs (status);
