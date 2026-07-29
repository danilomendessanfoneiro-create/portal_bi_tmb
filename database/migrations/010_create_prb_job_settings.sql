-- 010_create_prb_job_settings.sql

CREATE TABLE IF NOT EXISTS prb_job_settings (
    id              SERIAL PRIMARY KEY,
    job_id          VARCHAR(100) NOT NULL,
    local_time      VARCHAR(5) NOT NULL,
    timezone        VARCHAR(64) NOT NULL DEFAULT 'America/Sao_Paulo',
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    created_by      VARCHAR(100),
    created_on      TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by     VARCHAR(100),
    modified_on     TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_prb_job_settings_job UNIQUE (job_id),
    CONSTRAINT ck_prb_job_settings_time CHECK (local_time ~ '^[0-2][0-9]:[0-5][0-9]$')
);

INSERT INTO prb_job_settings (job_id, local_time, timezone, enabled, created_by, modified_by)
VALUES ('report_overdue_daily', '07:00', 'America/Sao_Paulo', TRUE, 'seed', 'seed')
ON CONFLICT (job_id) DO NOTHING;
