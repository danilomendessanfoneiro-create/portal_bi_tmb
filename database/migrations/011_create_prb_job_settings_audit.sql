-- 011_create_prb_job_settings_audit.sql

CREATE TABLE IF NOT EXISTS prb_job_settings_audit (
    id              INTEGER,
    job_id          VARCHAR(100),
    local_time      VARCHAR(5),
    timezone        VARCHAR(64),
    enabled         BOOLEAN,
    created_by      VARCHAR(100),
    created_on      TIMESTAMP WITHOUT TIME ZONE,
    modified_by     VARCHAR(100),
    modified_on     TIMESTAMP WITHOUT TIME ZONE,
    created_on_audit TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action          VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_job_settings_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_job_settings_audit_created
    ON prb_job_settings_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_job_settings_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_job_settings_audit (
            id, job_id, local_time, timezone, enabled,
            created_by, created_on, modified_by, modified_on,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.local_time, NEW.timezone, NEW.enabled,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_job_settings_audit (
            id, job_id, local_time, timezone, enabled,
            created_by, created_on, modified_by, modified_on,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.local_time, NEW.timezone, NEW.enabled,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_job_settings_audit (
            id, job_id, local_time, timezone, enabled,
            created_by, created_on, modified_by, modified_on,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.job_id, OLD.local_time, OLD.timezone, OLD.enabled,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_job_settings_audit ON prb_job_settings;
CREATE TRIGGER trg_prb_job_settings_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_job_settings
FOR EACH ROW
EXECUTE FUNCTION fn_prb_job_settings_audit();
