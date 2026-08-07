-- 038_create_prb_clients_audit.sql

CREATE TABLE IF NOT EXISTS prb_clients_audit (
    id                  INTEGER,
    name                VARCHAR(200),
    cnpj                VARCHAR(14),
    emails              TEXT,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_clients_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_clients_audit_created
    ON prb_clients_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_clients_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_clients_audit (
            id, name, cnpj, emails,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.name, NEW.cnpj, NEW.emails,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_clients_audit (
            id, name, cnpj, emails,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.name, NEW.cnpj, NEW.emails,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_clients_audit (
            id, name, cnpj, emails,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.name, OLD.cnpj, OLD.emails,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_clients_audit ON prb_clients;
CREATE TRIGGER trg_prb_clients_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_clients
FOR EACH ROW
EXECUTE FUNCTION fn_prb_clients_audit();
