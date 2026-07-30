-- 025_create_prb_import_audit.sql

CREATE TABLE IF NOT EXISTS prb_import_batches_audit (
    id                  INTEGER,
    file_name           VARCHAR(500),
    file_ext            VARCHAR(10),
    file_size_bytes     BIGINT,
    file_path           TEXT,
    file_mtime          TIMESTAMP WITHOUT TIME ZONE,
    status              VARCHAR(30),
    total_rows          INTEGER,
    valid_rows          INTEGER,
    error_rows          INTEGER,
    rows_processed      INTEGER,
    rows_inserted       INTEGER,
    rows_updated        INTEGER,
    progress_pct        NUMERIC(5, 2),
    validation_errors   JSONB,
    started_on          TIMESTAMP WITHOUT TIME ZONE,
    finished_on         TIMESTAMP WITHOUT TIME ZONE,
    duration_ms         INTEGER,
    error_message       TEXT,
    report_job_status   VARCHAR(30),
    report_job_message  TEXT,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_import_batches_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_import_batches_audit_created
    ON prb_import_batches_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_import_batches_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_import_batches_audit (
            id, file_name, file_ext, file_size_bytes, file_path, file_mtime, status,
            total_rows, valid_rows, error_rows, rows_processed, rows_inserted, rows_updated,
            progress_pct, validation_errors, started_on, finished_on, duration_ms, error_message,
            report_job_status, report_job_message, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.file_name, NEW.file_ext, NEW.file_size_bytes, NEW.file_path, NEW.file_mtime, NEW.status,
            NEW.total_rows, NEW.valid_rows, NEW.error_rows, NEW.rows_processed, NEW.rows_inserted, NEW.rows_updated,
            NEW.progress_pct, NEW.validation_errors, NEW.started_on, NEW.finished_on, NEW.duration_ms, NEW.error_message,
            NEW.report_job_status, NEW.report_job_message, NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_import_batches_audit (
            id, file_name, file_ext, file_size_bytes, file_path, file_mtime, status,
            total_rows, valid_rows, error_rows, rows_processed, rows_inserted, rows_updated,
            progress_pct, validation_errors, started_on, finished_on, duration_ms, error_message,
            report_job_status, report_job_message, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.file_name, NEW.file_ext, NEW.file_size_bytes, NEW.file_path, NEW.file_mtime, NEW.status,
            NEW.total_rows, NEW.valid_rows, NEW.error_rows, NEW.rows_processed, NEW.rows_inserted, NEW.rows_updated,
            NEW.progress_pct, NEW.validation_errors, NEW.started_on, NEW.finished_on, NEW.duration_ms, NEW.error_message,
            NEW.report_job_status, NEW.report_job_message, NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_import_batches_audit (
            id, file_name, file_ext, file_size_bytes, file_path, file_mtime, status,
            total_rows, valid_rows, error_rows, rows_processed, rows_inserted, rows_updated,
            progress_pct, validation_errors, started_on, finished_on, duration_ms, error_message,
            report_job_status, report_job_message, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.file_name, OLD.file_ext, OLD.file_size_bytes, OLD.file_path, OLD.file_mtime, OLD.status,
            OLD.total_rows, OLD.valid_rows, OLD.error_rows, OLD.rows_processed, OLD.rows_inserted, OLD.rows_updated,
            OLD.progress_pct, OLD.validation_errors, OLD.started_on, OLD.finished_on, OLD.duration_ms, OLD.error_message,
            OLD.report_job_status, OLD.report_job_message, OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_import_batches_audit ON prb_import_batches;
CREATE TRIGGER trg_prb_import_batches_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_import_batches
FOR EACH ROW
EXECUTE FUNCTION fn_prb_import_batches_audit();

CREATE TABLE IF NOT EXISTS prb_import_batch_items_audit (
    id                  INTEGER,
    batch_id            INTEGER,
    row_number          INTEGER,
    remessa_numero      VARCHAR(100),
    nro_entrega         VARCHAR(100),
    nota_fiscal         VARCHAR(100),
    cliente             VARCHAR(500),
    filial              VARCHAR(200),
    is_valid            BOOLEAN,
    error_message       TEXT,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_import_batch_items_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_import_batch_items_audit_created
    ON prb_import_batch_items_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_import_batch_items_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_import_batch_items_audit (
            id, batch_id, row_number, remessa_numero, nro_entrega, nota_fiscal, cliente, filial,
            is_valid, error_message, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.batch_id, NEW.row_number, NEW.remessa_numero, NEW.nro_entrega, NEW.nota_fiscal, NEW.cliente, NEW.filial,
            NEW.is_valid, NEW.error_message, NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_import_batch_items_audit (
            id, batch_id, row_number, remessa_numero, nro_entrega, nota_fiscal, cliente, filial,
            is_valid, error_message, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.batch_id, NEW.row_number, NEW.remessa_numero, NEW.nro_entrega, NEW.nota_fiscal, NEW.cliente, NEW.filial,
            NEW.is_valid, NEW.error_message, NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_import_batch_items_audit (
            id, batch_id, row_number, remessa_numero, nro_entrega, nota_fiscal, cliente, filial,
            is_valid, error_message, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.batch_id, OLD.row_number, OLD.remessa_numero, OLD.nro_entrega, OLD.nota_fiscal, OLD.cliente, OLD.filial,
            OLD.is_valid, OLD.error_message, OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_import_batch_items_audit ON prb_import_batch_items;
CREATE TRIGGER trg_prb_import_batch_items_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_import_batch_items
FOR EACH ROW
EXECUTE FUNCTION fn_prb_import_batch_items_audit();

CREATE TABLE IF NOT EXISTS prb_import_logs_audit (
    id                  INTEGER,
    batch_id            INTEGER,
    row_number          INTEGER,
    level               VARCHAR(20),
    message             TEXT,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_import_logs_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE OR REPLACE FUNCTION fn_prb_import_logs_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_import_logs_audit (
            id, batch_id, row_number, level, message, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.batch_id, NEW.row_number, NEW.level, NEW.message, NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_import_logs_audit (
            id, batch_id, row_number, level, message, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.batch_id, NEW.row_number, NEW.level, NEW.message, NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_import_logs_audit (
            id, batch_id, row_number, level, message, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.batch_id, OLD.row_number, OLD.level, OLD.message, OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_import_logs_audit ON prb_import_logs;
CREATE TRIGGER trg_prb_import_logs_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_import_logs
FOR EACH ROW
EXECUTE FUNCTION fn_prb_import_logs_audit();
