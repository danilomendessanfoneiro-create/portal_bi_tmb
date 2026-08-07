-- 035_create_prb_progress_snapshot_item_audit.sql

CREATE TABLE IF NOT EXISTS prb_progress_snapshot_item_audit (
    id                  BIGINT,
    snapshot_run_id     INTEGER,
    nro_entrega         VARCHAR(100),
    remessa_numero      VARCHAR(100),
    status              VARCHAR(100),
    filial              VARCHAR(200),
    cliente             VARCHAR(500),
    cnpj_cliente        VARCHAR(14),
    cidade_entrega      VARCHAR(200),
    uf_entrega          VARCHAR(10),
    motorista           VARCHAR(300),
    valor_total         NUMERIC(18, 2),
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_progress_snapshot_item_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_progress_snapshot_item_audit_created
    ON prb_progress_snapshot_item_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_progress_snapshot_item_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_progress_snapshot_item_audit (
            id, snapshot_run_id, nro_entrega, remessa_numero, status, filial, cliente, cnpj_cliente,
            cidade_entrega, uf_entrega, motorista, valor_total,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.snapshot_run_id, NEW.nro_entrega, NEW.remessa_numero, NEW.status, NEW.filial, NEW.cliente, NEW.cnpj_cliente,
            NEW.cidade_entrega, NEW.uf_entrega, NEW.motorista, NEW.valor_total,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_progress_snapshot_item_audit (
            id, snapshot_run_id, nro_entrega, remessa_numero, status, filial, cliente, cnpj_cliente,
            cidade_entrega, uf_entrega, motorista, valor_total,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.snapshot_run_id, NEW.nro_entrega, NEW.remessa_numero, NEW.status, NEW.filial, NEW.cliente, NEW.cnpj_cliente,
            NEW.cidade_entrega, NEW.uf_entrega, NEW.motorista, NEW.valor_total,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_progress_snapshot_item_audit (
            id, snapshot_run_id, nro_entrega, remessa_numero, status, filial, cliente, cnpj_cliente,
            cidade_entrega, uf_entrega, motorista, valor_total,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            OLD.id, OLD.snapshot_run_id, OLD.nro_entrega, OLD.remessa_numero, OLD.status, OLD.filial, OLD.cliente, OLD.cnpj_cliente,
            OLD.cidade_entrega, OLD.uf_entrega, OLD.motorista, OLD.valor_total,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled, NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_progress_snapshot_item_audit ON prb_progress_snapshot_item;
CREATE TRIGGER trg_prb_progress_snapshot_item_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_progress_snapshot_item
FOR EACH ROW
EXECUTE FUNCTION fn_prb_progress_snapshot_item_audit();
