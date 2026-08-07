-- 037_create_prb_clients.sql

CREATE TABLE IF NOT EXISTS prb_clients (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    cnpj                VARCHAR(14) NOT NULL,
    emails              TEXT,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_prb_clients_cnpj_enabled
    ON prb_clients (cnpj)
    WHERE enabled = TRUE;

CREATE INDEX IF NOT EXISTS ix_prb_clients_enabled ON prb_clients (enabled);
CREATE INDEX IF NOT EXISTS ix_prb_clients_name ON prb_clients (name);
CREATE INDEX IF NOT EXISTS ix_prb_clients_cnpj ON prb_clients (cnpj);
