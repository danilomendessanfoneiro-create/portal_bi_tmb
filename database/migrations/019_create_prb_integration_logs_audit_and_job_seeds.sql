-- 019_create_prb_integration_logs_audit_and_job_seeds.sql

CREATE TABLE IF NOT EXISTS prb_integration_logs_audit (
    id                  INTEGER,
    job_id              VARCHAR(100),
    business_date       DATE,
    status              VARCHAR(20),
    started_on          TIMESTAMP WITHOUT TIME ZONE,
    finished_on         TIMESTAMP WITHOUT TIME ZONE,
    duration_ms         INTEGER,
    pages_processed     INTEGER,
    rows_inserted       INTEGER,
    rows_updated        INTEGER,
    error_count         INTEGER,
    error_message       TEXT,
    filter_start        DATE,
    filter_end          DATE,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_integration_logs_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_integration_logs_audit_created
    ON prb_integration_logs_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_integration_logs_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_integration_logs_audit (
            id, job_id, business_date, status, started_on, finished_on, duration_ms,
            pages_processed, rows_inserted, rows_updated, error_count, error_message,
            filter_start, filter_end, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.business_date, NEW.status, NEW.started_on, NEW.finished_on, NEW.duration_ms,
            NEW.pages_processed, NEW.rows_inserted, NEW.rows_updated, NEW.error_count, NEW.error_message,
            NEW.filter_start, NEW.filter_end, NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_integration_logs_audit (
            id, job_id, business_date, status, started_on, finished_on, duration_ms,
            pages_processed, rows_inserted, rows_updated, error_count, error_message,
            filter_start, filter_end, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.business_date, NEW.status, NEW.started_on, NEW.finished_on, NEW.duration_ms,
            NEW.pages_processed, NEW.rows_inserted, NEW.rows_updated, NEW.error_count, NEW.error_message,
            NEW.filter_start, NEW.filter_end, NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_integration_logs_audit (
            id, job_id, business_date, status, started_on, finished_on, duration_ms,
            pages_processed, rows_inserted, rows_updated, error_count, error_message,
            filter_start, filter_end, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.job_id, OLD.business_date, OLD.status, OLD.started_on, OLD.finished_on, OLD.duration_ms,
            OLD.pages_processed, OLD.rows_inserted, OLD.rows_updated, OLD.error_count, OLD.error_message,
            OLD.filter_start, OLD.filter_end, OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_integration_logs_audit ON prb_integration_logs;
CREATE TRIGGER trg_prb_integration_logs_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_integration_logs
FOR EACH ROW
EXECUTE FUNCTION fn_prb_integration_logs_audit();

INSERT INTO prb_job_settings (
    job_id, local_time, timezone, enabled,
    display_name, frequency, weekday, day_of_month,
    created_by, modified_by
)
VALUES
    (
        'import_deliveries_initial', '03:00', 'America/Sao_Paulo', FALSE,
        'Migração Inicial (API Entregas)', 'daily', NULL, NULL,
        'seed', 'seed'
    ),
    (
        'import_deliveries_daily', '07:00', 'America/Sao_Paulo', TRUE,
        'Atualização Diária (API Entregas)', 'daily', NULL, NULL,
        'seed', 'seed'
    )
ON CONFLICT (job_id) DO UPDATE SET
    display_name = COALESCE(prb_job_settings.display_name, EXCLUDED.display_name),
    frequency = COALESCE(NULLIF(prb_job_settings.frequency, ''), EXCLUDED.frequency);
