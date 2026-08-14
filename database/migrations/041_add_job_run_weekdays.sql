-- 041_add_job_run_weekdays.sql
-- Dias da semana por automação (0=Domingo … 6=Sábado). Default: seg–sáb.
-- Jobs visíveis desativados; API permanece no banco desativada.

ALTER TABLE prb_job_settings
    ADD COLUMN IF NOT EXISTS run_weekdays SMALLINT[] NOT NULL DEFAULT '{1,2,3,4,5,6}';

ALTER TABLE prb_job_settings_audit
    ADD COLUMN IF NOT EXISTS run_weekdays SMALLINT[];

ALTER TABLE prb_job_settings
    DROP CONSTRAINT IF EXISTS ck_prb_job_settings_run_weekdays;
ALTER TABLE prb_job_settings
    ADD CONSTRAINT ck_prb_job_settings_run_weekdays CHECK (
        cardinality(run_weekdays) >= 1
        AND run_weekdays <@ ARRAY[0, 1, 2, 3, 4, 5, 6]::smallint[]
    );

CREATE OR REPLACE FUNCTION fn_prb_job_settings_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_job_settings_audit (
            id, job_id, local_time, timezone, enabled,
            display_name, frequency, weekday, day_of_month,
            tms_login_url, tms_username, tms_password_encrypted,
            run_weekdays,
            created_by, created_on, modified_by, modified_on,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.local_time, NEW.timezone, NEW.enabled,
            NEW.display_name, NEW.frequency, NEW.weekday, NEW.day_of_month,
            NEW.tms_login_url, NEW.tms_username, NEW.tms_password_encrypted,
            NEW.run_weekdays,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_job_settings_audit (
            id, job_id, local_time, timezone, enabled,
            display_name, frequency, weekday, day_of_month,
            tms_login_url, tms_username, tms_password_encrypted,
            run_weekdays,
            created_by, created_on, modified_by, modified_on,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.local_time, NEW.timezone, NEW.enabled,
            NEW.display_name, NEW.frequency, NEW.weekday, NEW.day_of_month,
            NEW.tms_login_url, NEW.tms_username, NEW.tms_password_encrypted,
            NEW.run_weekdays,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_job_settings_audit (
            id, job_id, local_time, timezone, enabled,
            display_name, frequency, weekday, day_of_month,
            tms_login_url, tms_username, tms_password_encrypted,
            run_weekdays,
            created_by, created_on, modified_by, modified_on,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.job_id, OLD.local_time, OLD.timezone, OLD.enabled,
            OLD.display_name, OLD.frequency, OLD.weekday, OLD.day_of_month,
            OLD.tms_login_url, OLD.tms_username, OLD.tms_password_encrypted,
            OLD.run_weekdays,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

UPDATE prb_job_settings
SET local_time = '05:00',
    enabled = FALSE,
    run_weekdays = '{1,2,3,4,5,6}',
    modified_by = 'seed',
    modified_on = NOW()
WHERE job_id = 'fetch_tmselite_spreadsheet';

UPDATE prb_job_settings
SET local_time = '08:00',
    enabled = FALSE,
    run_weekdays = '{1,2,3,4,5,6}',
    modified_by = 'seed',
    modified_on = NOW()
WHERE job_id IN ('report_branch_daily', 'report_client_daily', 'report_managerial');

UPDATE prb_job_settings
SET enabled = FALSE,
    run_weekdays = '{1,2,3,4,5,6}',
    modified_by = 'seed',
    modified_on = NOW()
WHERE job_id IN ('import_deliveries_daily', 'import_deliveries_initial');
