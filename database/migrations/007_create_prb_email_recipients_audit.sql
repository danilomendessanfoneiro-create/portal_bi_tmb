-- 007_create_prb_email_recipients_audit.sql

CREATE TABLE IF NOT EXISTS prb_email_recipients_audit (
    id                  INTEGER,
    name                VARCHAR(200),
    email               VARCHAR(255),
    role_title          VARCHAR(200),
    department          VARCHAR(200),
    receive_daily       BOOLEAN,
    receive_weekly      BOOLEAN,
    receive_monthly     BOOLEAN,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_email_recipients_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_email_recipients_audit_created
    ON prb_email_recipients_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_email_recipients_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_email_recipients_audit (
            id, name, email, role_title, department,
            receive_daily, receive_weekly, receive_monthly,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.name, NEW.email, NEW.role_title, NEW.department,
            NEW.receive_daily, NEW.receive_weekly, NEW.receive_monthly,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_email_recipients_audit (
            id, name, email, role_title, department,
            receive_daily, receive_weekly, receive_monthly,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            NEW.id, NEW.name, NEW.email, NEW.role_title, NEW.department,
            NEW.receive_daily, NEW.receive_weekly, NEW.receive_monthly,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled,
            NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_email_recipients_audit (
            id, name, email, role_title, department,
            receive_daily, receive_weekly, receive_monthly,
            created_by, created_on, modified_by, modified_on, enabled,
            created_on_audit, action
        ) VALUES (
            OLD.id, OLD.name, OLD.email, OLD.role_title, OLD.department,
            OLD.receive_daily, OLD.receive_weekly, OLD.receive_monthly,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled,
            NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_email_recipients_audit ON prb_email_recipients;
CREATE TRIGGER trg_prb_email_recipients_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_email_recipients
FOR EACH ROW
EXECUTE FUNCTION fn_prb_email_recipients_audit();
