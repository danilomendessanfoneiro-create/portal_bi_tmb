-- 040_add_tms_rpa_job_settings.sql
-- Credenciais da coleta TMS Elite na automação (senha cifrada, padrão SMTP).

ALTER TABLE prb_job_settings
    ADD COLUMN IF NOT EXISTS tms_login_url VARCHAR(500),
    ADD COLUMN IF NOT EXISTS tms_username VARCHAR(200),
    ADD COLUMN IF NOT EXISTS tms_password_encrypted TEXT;

ALTER TABLE prb_job_settings_audit
    ADD COLUMN IF NOT EXISTS tms_login_url VARCHAR(500),
    ADD COLUMN IF NOT EXISTS tms_username VARCHAR(200),
    ADD COLUMN IF NOT EXISTS tms_password_encrypted TEXT;

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
            created_by, created_on, modified_by, modified_on,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.local_time, NEW.timezone, NEW.enabled,
            NEW.display_name, NEW.frequency, NEW.weekday, NEW.day_of_month,
            NEW.tms_login_url, NEW.tms_username, NEW.tms_password_encrypted,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_job_settings_audit (
            id, job_id, local_time, timezone, enabled,
            display_name, frequency, weekday, day_of_month,
            tms_login_url, tms_username, tms_password_encrypted,
            created_by, created_on, modified_by, modified_on,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.local_time, NEW.timezone, NEW.enabled,
            NEW.display_name, NEW.frequency, NEW.weekday, NEW.day_of_month,
            NEW.tms_login_url, NEW.tms_username, NEW.tms_password_encrypted,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_job_settings_audit (
            id, job_id, local_time, timezone, enabled,
            display_name, frequency, weekday, day_of_month,
            tms_login_url, tms_username, tms_password_encrypted,
            created_by, created_on, modified_by, modified_on,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.job_id, OLD.local_time, OLD.timezone, OLD.enabled,
            OLD.display_name, OLD.frequency, OLD.weekday, OLD.day_of_month,
            OLD.tms_login_url, OLD.tms_username, OLD.tms_password_encrypted,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

INSERT INTO prb_job_settings (
    job_id, local_time, timezone, enabled,
    display_name, frequency, weekday, day_of_month,
    tms_login_url, created_by, modified_by
)
VALUES (
    'fetch_tmselite_spreadsheet', '05:00', 'America/Sao_Paulo', FALSE,
    'Coleta da planilha TMS Elite', 'daily', NULL, NULL,
    'https://tmblogistica.tmselite.com/login', 'seed', 'seed'
)
ON CONFLICT (job_id) DO UPDATE SET
    display_name = COALESCE(prb_job_settings.display_name, EXCLUDED.display_name),
    tms_login_url = COALESCE(prb_job_settings.tms_login_url, EXCLUDED.tms_login_url),
    frequency = COALESCE(NULLIF(prb_job_settings.frequency, ''), EXCLUDED.frequency);
