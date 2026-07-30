-- 020_create_prb_bi_snapshot_run.sql

CREATE TABLE IF NOT EXISTS prb_bi_snapshot_run (
    id                  SERIAL PRIMARY KEY,
    business_date       DATE NOT NULL,
    captured_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    source_job_id       VARCHAR(100),
    source_run_id       INTEGER,
    rule_version        VARCHAR(40) NOT NULL DEFAULT 'macros-v1',
    total_overdue       INTEGER NOT NULL DEFAULT 0,
    total_value_overdue NUMERIC(18, 2),
    source              VARCHAR(40) NOT NULL DEFAULT 'job',
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_prb_bi_snapshot_run_business_date UNIQUE (business_date),
    CONSTRAINT ck_prb_bi_snapshot_run_source CHECK (source IN ('job', 'seed-demo'))
);

CREATE INDEX IF NOT EXISTS ix_prb_bi_snapshot_run_captured
    ON prb_bi_snapshot_run (captured_on DESC);

CREATE INDEX IF NOT EXISTS ix_prb_bi_snapshot_run_source
    ON prb_bi_snapshot_run (source);
