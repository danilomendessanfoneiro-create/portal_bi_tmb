-- 005_create_prb_smtp_settings_audit.sql

CREATE TABLE IF NOT EXISTS prb_smtp_settings_audit (
    id                  INTEGER,
    name                VARCHAR(200),
    host                VARCHAR(255),
    port                INTEGER,
    username            VARCHAR(255),
    password_encrypted  TEXT,
    use_tls             BOOLEAN,
    sender_email        VARCHAR(255),
    sender_name         VARCHAR(200),
    timeout_seconds     INTEGER,
    is_default          BOOLEAN,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_smtp_settings_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_smtp_settings_audit_created
    ON prb_smtp_settings_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_smtp_settings_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_smtp_settings_audit (
            id, name, host, port, username, password_encrypted, use_tls,
            sender_email, sender_name, timeout_seconds, is_default,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.name, NEW.host, NEW.port, NEW.username, NEW.password_encrypted, NEW.use_tls,
            NEW.sender_email, NEW.sender_name, NEW.timeout_seconds, NEW.is_default,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_smtp_settings_audit (
            id, name, host, port, username, password_encrypted, use_tls,
            sender_email, sender_name, timeout_seconds, is_default,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.name, NEW.host, NEW.port, NEW.username, NEW.password_encrypted, NEW.use_tls,
            NEW.sender_email, NEW.sender_name, NEW.timeout_seconds, NEW.is_default,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_smtp_settings_audit (
            id, name, host, port, username, password_encrypted, use_tls,
            sender_email, sender_name, timeout_seconds, is_default,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.name, OLD.host, OLD.port, OLD.username, OLD.password_encrypted, OLD.use_tls,
            OLD.sender_email, OLD.sender_name, OLD.timeout_seconds, OLD.is_default,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_smtp_settings_audit ON prb_smtp_settings;
CREATE TRIGGER trg_prb_smtp_settings_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_smtp_settings
FOR EACH ROW
EXECUTE FUNCTION fn_prb_smtp_settings_audit();
