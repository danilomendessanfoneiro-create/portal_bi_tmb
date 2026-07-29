-- 009_create_prb_job_runs_audit.sql

CREATE TABLE IF NOT EXISTS prb_job_runs_audit (
    id              INTEGER,
    job_id          VARCHAR(100),
    business_date   DATE,
    status          VARCHAR(20),
    started_on      TIMESTAMP WITHOUT TIME ZONE,
    finished_on     TIMESTAMP WITHOUT TIME ZONE,
    message         TEXT,
    metrics_json    TEXT,
    artifact_path   TEXT,
    created_by      VARCHAR(100),
    created_on      TIMESTAMP WITHOUT TIME ZONE,
    modified_by     VARCHAR(100),
    modified_on     TIMESTAMP WITHOUT TIME ZONE,
    enabled         BOOLEAN,
    created_on_audit TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action          VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_job_runs_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_job_runs_audit_created
    ON prb_job_runs_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_job_runs_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_job_runs_audit (
            id, job_id, business_date, status, started_on, finished_on, message,
            metrics_json, artifact_path, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.business_date, NEW.status, NEW.started_on, NEW.finished_on, NEW.message,
            NEW.metrics_json, NEW.artifact_path, NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_job_runs_audit (
            id, job_id, business_date, status, started_on, finished_on, message,
            metrics_json, artifact_path, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.business_date, NEW.status, NEW.started_on, NEW.finished_on, NEW.message,
            NEW.metrics_json, NEW.artifact_path, NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_job_runs_audit (
            id, job_id, business_date, status, started_on, finished_on, message,
            metrics_json, artifact_path, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.job_id, OLD.business_date, OLD.status, OLD.started_on, OLD.finished_on, OLD.message,
            OLD.metrics_json, OLD.artifact_path, OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_job_runs_audit ON prb_job_runs;
CREATE TRIGGER trg_prb_job_runs_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_job_runs
FOR EACH ROW
EXECUTE FUNCTION fn_prb_job_runs_audit();
