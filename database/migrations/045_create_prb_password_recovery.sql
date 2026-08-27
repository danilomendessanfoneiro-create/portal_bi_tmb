-- 045_create_prb_password_recovery.sql
-- Tokens de recuperação de senha (armazena somente hash do token)

CREATE TABLE IF NOT EXISTS prb_password_recovery (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES prb_users (id),
    token_hash      VARCHAR(128) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    used_at         TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL DEFAULT 'Pending',
    CONSTRAINT ck_prb_password_recovery_status
        CHECK (status IN ('Pending', 'Used', 'Expired', 'Revoked')),
    CONSTRAINT uq_prb_password_recovery_token_hash UNIQUE (token_hash)
);

CREATE INDEX IF NOT EXISTS ix_prb_password_recovery_user_id
    ON prb_password_recovery (user_id);

CREATE INDEX IF NOT EXISTS ix_prb_password_recovery_active
    ON prb_password_recovery (user_id, status, expires_at)
    WHERE status = 'Pending';
