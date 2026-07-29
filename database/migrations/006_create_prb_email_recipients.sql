-- 006_create_prb_email_recipients.sql

CREATE TABLE IF NOT EXISTS prb_email_recipients (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    email               VARCHAR(255) NOT NULL,
    role_title          VARCHAR(200),
    department          VARCHAR(200),
    receive_daily       BOOLEAN NOT NULL DEFAULT TRUE,
    receive_weekly      BOOLEAN NOT NULL DEFAULT FALSE,
    receive_monthly     BOOLEAN NOT NULL DEFAULT FALSE,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_prb_email_recipients_email UNIQUE (email)
);

CREATE INDEX IF NOT EXISTS ix_prb_email_recipients_enabled ON prb_email_recipients (enabled);
CREATE INDEX IF NOT EXISTS ix_prb_email_recipients_email ON prb_email_recipients (email);
