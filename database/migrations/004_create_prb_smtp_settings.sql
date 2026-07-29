-- 004_create_prb_smtp_settings.sql

CREATE TABLE IF NOT EXISTS prb_smtp_settings (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    host                VARCHAR(255) NOT NULL,
    port                INTEGER NOT NULL,
    username            VARCHAR(255) NOT NULL,
    password_encrypted  TEXT NOT NULL,
    use_tls             BOOLEAN NOT NULL DEFAULT TRUE,
    sender_email        VARCHAR(255) NOT NULL,
    sender_name         VARCHAR(200) NOT NULL,
    timeout_seconds     INTEGER,
    is_default          BOOLEAN NOT NULL DEFAULT FALSE,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT ck_prb_smtp_settings_port CHECK (port > 0 AND port <= 65535)
);

CREATE INDEX IF NOT EXISTS ix_prb_smtp_settings_enabled ON prb_smtp_settings (enabled);
CREATE INDEX IF NOT EXISTS ix_prb_smtp_settings_default ON prb_smtp_settings (is_default);

CREATE UNIQUE INDEX IF NOT EXISTS uq_prb_smtp_settings_one_default
    ON prb_smtp_settings ((1))
    WHERE is_default = TRUE AND enabled = TRUE;
