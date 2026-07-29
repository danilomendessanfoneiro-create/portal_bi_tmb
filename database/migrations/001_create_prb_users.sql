-- 001_create_prb_users.sql
-- Portal BI users (each user represents a branch / admin)

CREATE TABLE IF NOT EXISTS prb_users (
    id              SERIAL PRIMARY KEY,
    login           VARCHAR(100) NOT NULL,
    password_hash   VARCHAR(128) NOT NULL,
    profile         VARCHAR(20)  NOT NULL,
    branch          VARCHAR(200),
    display_name    VARCHAR(200),
    name            VARCHAR(200),
    code            VARCHAR(100),
    created_by      VARCHAR(100),
    created_on      TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by     VARCHAR(100),
    modified_on     TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_prb_users_login UNIQUE (login),
    CONSTRAINT ck_prb_users_profile CHECK (profile IN ('admin', 'filial'))
);

CREATE INDEX IF NOT EXISTS ix_prb_users_branch ON prb_users (branch);
CREATE INDEX IF NOT EXISTS ix_prb_users_enabled ON prb_users (enabled);
CREATE INDEX IF NOT EXISTS ix_prb_users_profile ON prb_users (profile);
