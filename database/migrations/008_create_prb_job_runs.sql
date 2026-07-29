-- 008_create_prb_job_runs.sql

CREATE TABLE IF NOT EXISTS prb_job_runs (
    id              SERIAL PRIMARY KEY,
    job_id          VARCHAR(100) NOT NULL,
    business_date   DATE NOT NULL,
    status          VARCHAR(20) NOT NULL,
    started_on      TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    finished_on     TIMESTAMP WITHOUT TIME ZONE,
    message         TEXT,
    metrics_json    TEXT,
    artifact_path   TEXT,
    created_by      VARCHAR(100),
    created_on      TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by     VARCHAR(100),
    modified_on     TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT ck_prb_job_runs_status
        CHECK (status IN ('running', 'success', 'failed', 'skipped'))
);

CREATE INDEX IF NOT EXISTS ix_prb_job_runs_job_date_status
    ON prb_job_runs (job_id, business_date, status);

CREATE INDEX IF NOT EXISTS ix_prb_job_runs_enabled ON prb_job_runs (enabled);
