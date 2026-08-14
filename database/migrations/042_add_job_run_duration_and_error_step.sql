-- 042_add_job_run_duration_and_error_step.sql
-- Duração e etapa da falha no histórico de execuções (prb_job_runs).

ALTER TABLE prb_job_runs
    ADD COLUMN IF NOT EXISTS duration_ms INTEGER,
    ADD COLUMN IF NOT EXISTS error_step VARCHAR(120);

ALTER TABLE prb_job_runs_audit
    ADD COLUMN IF NOT EXISTS duration_ms INTEGER,
    ADD COLUMN IF NOT EXISTS error_step VARCHAR(120);

CREATE OR REPLACE FUNCTION fn_prb_job_runs_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_job_runs_audit (
            id, job_id, business_date, status, started_on, finished_on, message,
            metrics_json, artifact_path, duration_ms, error_step,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.business_date, NEW.status, NEW.started_on, NEW.finished_on, NEW.message,
            NEW.metrics_json, NEW.artifact_path, NEW.duration_ms, NEW.error_step,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_job_runs_audit (
            id, job_id, business_date, status, started_on, finished_on, message,
            metrics_json, artifact_path, duration_ms, error_step,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.business_date, NEW.status, NEW.started_on, NEW.finished_on, NEW.message,
            NEW.metrics_json, NEW.artifact_path, NEW.duration_ms, NEW.error_step,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_job_runs_audit (
            id, job_id, business_date, status, started_on, finished_on, message,
            metrics_json, artifact_path, duration_ms, error_step,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.job_id, OLD.business_date, OLD.status, OLD.started_on, OLD.finished_on, OLD.message,
            OLD.metrics_json, OLD.artifact_path, OLD.duration_ms, OLD.error_step,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;
