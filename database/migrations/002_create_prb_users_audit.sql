-- 002_create_prb_users_audit.sql
-- Audit replica for prb_users + automatic trigger

CREATE TABLE IF NOT EXISTS prb_users_audit (
    id                  INTEGER,
    login               VARCHAR(100),
    password_hash       VARCHAR(128),
    profile             VARCHAR(20),
    branch              VARCHAR(200),
    display_name        VARCHAR(200),
    name                VARCHAR(200),
    code                VARCHAR(100),
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_users_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_users_audit_login ON prb_users_audit (login);
CREATE INDEX IF NOT EXISTS ix_prb_users_audit_created ON prb_users_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_users_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_users_audit (
            id, login, password_hash, profile, branch, display_name, name, code,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.login, NEW.password_hash, NEW.profile, NEW.branch,
            NEW.display_name, NEW.name, NEW.code,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_users_audit (
            id, login, password_hash, profile, branch, display_name, name, code,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.login, NEW.password_hash, NEW.profile, NEW.branch,
            NEW.display_name, NEW.name, NEW.code,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_users_audit (
            id, login, password_hash, profile, branch, display_name, name, code,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.login, OLD.password_hash, OLD.profile, OLD.branch,
            OLD.display_name, OLD.name, OLD.code,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_users_audit ON prb_users;
CREATE TRIGGER trg_prb_users_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_users
FOR EACH ROW
EXECUTE FUNCTION fn_prb_users_audit();
