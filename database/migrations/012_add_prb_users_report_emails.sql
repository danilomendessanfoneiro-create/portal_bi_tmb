-- 012_add_prb_users_report_emails.sql
-- E-mails do relatório diário por usuário filial (separados por ;)

ALTER TABLE prb_users
    ADD COLUMN IF NOT EXISTS report_emails TEXT;

ALTER TABLE prb_users_audit
    ADD COLUMN IF NOT EXISTS report_emails TEXT;

CREATE OR REPLACE FUNCTION fn_prb_users_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_users_audit (
            id, login, password_hash, profile, branch, display_name, name, code,
            report_emails,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.login, NEW.password_hash, NEW.profile, NEW.branch,
            NEW.display_name, NEW.name, NEW.code,
            NEW.report_emails,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_users_audit (
            id, login, password_hash, profile, branch, display_name, name, code,
            report_emails,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.login, NEW.password_hash, NEW.profile, NEW.branch,
            NEW.display_name, NEW.name, NEW.code,
            NEW.report_emails,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_users_audit (
            id, login, password_hash, profile, branch, display_name, name, code,
            report_emails,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.login, OLD.password_hash, OLD.profile, OLD.branch,
            OLD.display_name, OLD.name, OLD.code,
            OLD.report_emails,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;
