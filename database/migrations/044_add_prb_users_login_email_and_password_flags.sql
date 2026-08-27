-- 044_add_prb_users_login_email_and_password_flags.sql
-- E-mail de login + flags de senha provisória

ALTER TABLE prb_users
    ADD COLUMN IF NOT EXISTS login_email VARCHAR(320),
    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS temporary_password_expires_at TIMESTAMPTZ;

ALTER TABLE prb_users_audit
    ADD COLUMN IF NOT EXISTS login_email VARCHAR(320),
    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN,
    ADD COLUMN IF NOT EXISTS temporary_password_expires_at TIMESTAMPTZ;

-- Unicidade case-insensitive; múltiplos NULL permitidos
CREATE UNIQUE INDEX IF NOT EXISTS uq_prb_users_login_email_lower
    ON prb_users (lower(login_email))
    WHERE login_email IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_prb_users_must_change_password
    ON prb_users (must_change_password)
    WHERE must_change_password = TRUE;

CREATE OR REPLACE FUNCTION fn_prb_users_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_users_audit (
            id, login, password_hash, profile, branch, display_name, name, code,
            report_emails, login_email, must_change_password, temporary_password_expires_at,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.login, NEW.password_hash, NEW.profile, NEW.branch,
            NEW.display_name, NEW.name, NEW.code,
            NEW.report_emails, NEW.login_email, NEW.must_change_password,
            NEW.temporary_password_expires_at,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_users_audit (
            id, login, password_hash, profile, branch, display_name, name, code,
            report_emails, login_email, must_change_password, temporary_password_expires_at,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.login, NEW.password_hash, NEW.profile, NEW.branch,
            NEW.display_name, NEW.name, NEW.code,
            NEW.report_emails, NEW.login_email, NEW.must_change_password,
            NEW.temporary_password_expires_at,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_users_audit (
            id, login, password_hash, profile, branch, display_name, name, code,
            report_emails, login_email, must_change_password, temporary_password_expires_at,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.login, OLD.password_hash, OLD.profile, OLD.branch,
            OLD.display_name, OLD.name, OLD.code,
            OLD.report_emails, OLD.login_email, OLD.must_change_password,
            OLD.temporary_password_expires_at,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;
