-- 021_create_prb_bi_snapshot_run_audit.sql

CREATE TABLE IF NOT EXISTS prb_bi_snapshot_run_audit (
    id                  INTEGER,
    business_date       DATE,
    captured_on         TIMESTAMP WITHOUT TIME ZONE,
    source_job_id       VARCHAR(100),
    source_run_id       INTEGER,
    rule_version        VARCHAR(40),
    total_overdue       INTEGER,
    total_value_overdue NUMERIC(18, 2),
    source              VARCHAR(40),
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_bi_snapshot_run_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_bi_snapshot_run_audit_created
    ON prb_bi_snapshot_run_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_bi_snapshot_run_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_bi_snapshot_run_audit (
            id, business_date, captured_on, source_job_id, source_run_id, rule_version,
            total_overdue, total_value_overdue, source,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.business_date, NEW.captured_on, NEW.source_job_id, NEW.source_run_id, NEW.rule_version,
            NEW.total_overdue, NEW.total_value_overdue, NEW.source,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_bi_snapshot_run_audit (
            id, business_date, captured_on, source_job_id, source_run_id, rule_version,
            total_overdue, total_value_overdue, source,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.business_date, NEW.captured_on, NEW.source_job_id, NEW.source_run_id, NEW.rule_version,
            NEW.total_overdue, NEW.total_value_overdue, NEW.source,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_bi_snapshot_run_audit (
            id, business_date, captured_on, source_job_id, source_run_id, rule_version,
            total_overdue, total_value_overdue, source,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            OLD.id, OLD.business_date, OLD.captured_on, OLD.source_job_id, OLD.source_run_id, OLD.rule_version,
            OLD.total_overdue, OLD.total_value_overdue, OLD.source,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled, NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_bi_snapshot_run_audit ON prb_bi_snapshot_run;
CREATE TRIGGER trg_prb_bi_snapshot_run_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_bi_snapshot_run
FOR EACH ROW
EXECUTE FUNCTION fn_prb_bi_snapshot_run_audit();
