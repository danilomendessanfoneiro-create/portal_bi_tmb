-- 014_create_prb_api_settings.sql

CREATE TABLE IF NOT EXISTS prb_api_settings (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    base_url            VARCHAR(500) NOT NULL,
    endpoint            VARCHAR(500) NOT NULL,
    token_encrypted     TEXT NOT NULL,
    timeout_seconds     INTEGER NOT NULL DEFAULT 60,
    page_size           INTEGER NOT NULL DEFAULT 500,
    initial_load_days   INTEGER NOT NULL DEFAULT 90,
    is_default          BOOLEAN NOT NULL DEFAULT FALSE,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT ck_prb_api_settings_timeout CHECK (timeout_seconds > 0 AND timeout_seconds <= 600),
    CONSTRAINT ck_prb_api_settings_page_size CHECK (page_size > 0 AND page_size <= 5000),
    CONSTRAINT ck_prb_api_settings_initial_days CHECK (initial_load_days > 0 AND initial_load_days <= 3650)
);

CREATE INDEX IF NOT EXISTS ix_prb_api_settings_enabled ON prb_api_settings (enabled);
CREATE INDEX IF NOT EXISTS ix_prb_api_settings_default ON prb_api_settings (is_default);

CREATE UNIQUE INDEX IF NOT EXISTS uq_prb_api_settings_one_default
    ON prb_api_settings ((1))
    WHERE is_default = TRUE AND enabled = TRUE;
