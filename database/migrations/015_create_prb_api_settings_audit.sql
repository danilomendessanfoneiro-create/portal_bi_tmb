-- 015_create_prb_api_settings_audit.sql

CREATE TABLE IF NOT EXISTS prb_api_settings_audit (
    id                  INTEGER,
    name                VARCHAR(200),
    base_url            VARCHAR(500),
    endpoint            VARCHAR(500),
    token_encrypted     TEXT,
    timeout_seconds     INTEGER,
    page_size           INTEGER,
    initial_load_days   INTEGER,
    is_default          BOOLEAN,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_api_settings_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_api_settings_audit_created
    ON prb_api_settings_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_api_settings_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_api_settings_audit (
            id, name, base_url, endpoint, token_encrypted, timeout_seconds, page_size,
            initial_load_days, is_default, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.name, NEW.base_url, NEW.endpoint, NEW.token_encrypted, NEW.timeout_seconds, NEW.page_size,
            NEW.initial_load_days, NEW.is_default, NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_api_settings_audit (
            id, name, base_url, endpoint, token_encrypted, timeout_seconds, page_size,
            initial_load_days, is_default, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.name, NEW.base_url, NEW.endpoint, NEW.token_encrypted, NEW.timeout_seconds, NEW.page_size,
            NEW.initial_load_days, NEW.is_default, NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_api_settings_audit (
            id, name, base_url, endpoint, token_encrypted, timeout_seconds, page_size,
            initial_load_days, is_default, created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.name, OLD.base_url, OLD.endpoint, OLD.token_encrypted, OLD.timeout_seconds, OLD.page_size,
            OLD.initial_load_days, OLD.is_default, OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_api_settings_audit ON prb_api_settings;
CREATE TRIGGER trg_prb_api_settings_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_api_settings
FOR EACH ROW
EXECUTE FUNCTION fn_prb_api_settings_audit();
