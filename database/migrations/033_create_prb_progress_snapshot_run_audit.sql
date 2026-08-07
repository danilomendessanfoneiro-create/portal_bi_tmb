-- 033_create_prb_progress_snapshot_run_audit.sql

CREATE TABLE IF NOT EXISTS prb_progress_snapshot_run_audit (
    id                  INTEGER,
    import_batch_id     INTEGER,
    captured_at         TIMESTAMPTZ,
    source              VARCHAR(40),
    row_count           INTEGER,
    rule_version        VARCHAR(40),
    notes               TEXT,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_progress_snapshot_run_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_progress_snapshot_run_audit_created
    ON prb_progress_snapshot_run_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_progress_snapshot_run_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_progress_snapshot_run_audit (
            id, import_batch_id, captured_at, source, row_count, rule_version, notes,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.import_batch_id, NEW.captured_at, NEW.source, NEW.row_count, NEW.rule_version, NEW.notes,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_progress_snapshot_run_audit (
            id, import_batch_id, captured_at, source, row_count, rule_version, notes,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.import_batch_id, NEW.captured_at, NEW.source, NEW.row_count, NEW.rule_version, NEW.notes,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_progress_snapshot_run_audit (
            id, import_batch_id, captured_at, source, row_count, rule_version, notes,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            OLD.id, OLD.import_batch_id, OLD.captured_at, OLD.source, OLD.row_count, OLD.rule_version, OLD.notes,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled, NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_progress_snapshot_run_audit ON prb_progress_snapshot_run;
CREATE TRIGGER trg_prb_progress_snapshot_run_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_progress_snapshot_run
FOR EACH ROW
EXECUTE FUNCTION fn_prb_progress_snapshot_run_audit();
