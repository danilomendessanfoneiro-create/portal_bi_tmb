-- 013_extend_prb_job_settings_automations.sql
-- Parametrização independente: display_name, frequency, weekday, day_of_month
-- Duas automações: filiais (daily) + gerencial (daily/weekly/monthly)

ALTER TABLE prb_job_settings
    ADD COLUMN IF NOT EXISTS display_name VARCHAR(200),
    ADD COLUMN IF NOT EXISTS frequency VARCHAR(20) NOT NULL DEFAULT 'daily',
    ADD COLUMN IF NOT EXISTS weekday SMALLINT,
    ADD COLUMN IF NOT EXISTS day_of_month SMALLINT;

ALTER TABLE prb_job_settings
    DROP CONSTRAINT IF EXISTS ck_prb_job_settings_frequency;
ALTER TABLE prb_job_settings
    ADD CONSTRAINT ck_prb_job_settings_frequency
    CHECK (frequency IN ('daily', 'weekly', 'monthly'));

ALTER TABLE prb_job_settings
    DROP CONSTRAINT IF EXISTS ck_prb_job_settings_weekday;
ALTER TABLE prb_job_settings
    ADD CONSTRAINT ck_prb_job_settings_weekday
    CHECK (weekday IS NULL OR (weekday >= 0 AND weekday <= 6));

ALTER TABLE prb_job_settings
    DROP CONSTRAINT IF EXISTS ck_prb_job_settings_day_of_month;
ALTER TABLE prb_job_settings
    ADD CONSTRAINT ck_prb_job_settings_day_of_month
    CHECK (day_of_month IS NULL OR (day_of_month >= 1 AND day_of_month <= 31));

ALTER TABLE prb_job_settings_audit
    ADD COLUMN IF NOT EXISTS display_name VARCHAR(200),
    ADD COLUMN IF NOT EXISTS frequency VARCHAR(20),
    ADD COLUMN IF NOT EXISTS weekday SMALLINT,
    ADD COLUMN IF NOT EXISTS day_of_month SMALLINT;

CREATE OR REPLACE FUNCTION fn_prb_job_settings_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_job_settings_audit (
            id, job_id, local_time, timezone, enabled,
            display_name, frequency, weekday, day_of_month,
            created_by, created_on, modified_by, modified_on,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.local_time, NEW.timezone, NEW.enabled,
            NEW.display_name, NEW.frequency, NEW.weekday, NEW.day_of_month,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_job_settings_audit (
            id, job_id, local_time, timezone, enabled,
            display_name, frequency, weekday, day_of_month,
            created_by, created_on, modified_by, modified_on,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.job_id, NEW.local_time, NEW.timezone, NEW.enabled,
            NEW.display_name, NEW.frequency, NEW.weekday, NEW.day_of_month,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_job_settings_audit (
            id, job_id, local_time, timezone, enabled,
            display_name, frequency, weekday, day_of_month,
            created_by, created_on, modified_by, modified_on,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.job_id, OLD.local_time, OLD.timezone, OLD.enabled,
            OLD.display_name, OLD.frequency, OLD.weekday, OLD.day_of_month,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

-- Migrar job legado → automação de filiais
UPDATE prb_job_settings
SET
    job_id = 'report_branch_daily',
    display_name = 'Envio Diário de Relatórios das Filiais',
    frequency = 'daily',
    weekday = NULL,
    day_of_month = NULL,
    modified_by = 'migration_013',
    modified_on = NOW()
WHERE job_id = 'report_overdue_daily';

INSERT INTO prb_job_settings (
    job_id, local_time, timezone, enabled,
    display_name, frequency, weekday, day_of_month,
    created_by, modified_by
)
VALUES (
    'report_branch_daily', '07:00', 'America/Sao_Paulo', TRUE,
    'Envio Diário de Relatórios das Filiais', 'daily', NULL, NULL,
    'seed', 'seed'
)
ON CONFLICT (job_id) DO UPDATE SET
    display_name = COALESCE(prb_job_settings.display_name, EXCLUDED.display_name),
    frequency = COALESCE(NULLIF(prb_job_settings.frequency, ''), EXCLUDED.frequency);

INSERT INTO prb_job_settings (
    job_id, local_time, timezone, enabled,
    display_name, frequency, weekday, day_of_month,
    created_by, modified_by
)
VALUES (
    'report_managerial', '07:00', 'America/Sao_Paulo', TRUE,
    'Relatório Gerencial', 'daily', NULL, NULL,
    'seed', 'seed'
)
ON CONFLICT (job_id) DO UPDATE SET
    display_name = COALESCE(prb_job_settings.display_name, EXCLUDED.display_name),
    frequency = COALESCE(NULLIF(prb_job_settings.frequency, ''), EXCLUDED.frequency);
