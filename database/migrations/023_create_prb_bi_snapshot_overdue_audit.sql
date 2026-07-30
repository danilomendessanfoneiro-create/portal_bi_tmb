-- 023_create_prb_bi_snapshot_overdue_audit.sql

CREATE TABLE IF NOT EXISTS prb_bi_snapshot_overdue_audit (
    id                  INTEGER,
    snapshot_run_id     INTEGER,
    business_date       DATE,
    remessa_numero      VARCHAR(100),
    nro_entrega         VARCHAR(100),
    nota_fiscal         VARCHAR(100),
    filial              VARCHAR(200),
    cliente             VARCHAR(500),
    cidade_entrega      VARCHAR(200),
    uf_entrega          VARCHAR(10),
    status              VARCHAR(100),
    motorista           VARCHAR(300),
    dias_atraso         INTEGER,
    valor_total         NUMERIC(18, 2),
    prazo_considerado   TIMESTAMP WITHOUT TIME ZONE,
    status_prazo        VARCHAR(40),
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_bi_snapshot_overdue_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_bi_snapshot_overdue_audit_created
    ON prb_bi_snapshot_overdue_audit (created_on_audit);

CREATE OR REPLACE FUNCTION fn_prb_bi_snapshot_overdue_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_bi_snapshot_overdue_audit (
            id, snapshot_run_id, business_date, remessa_numero, nro_entrega, nota_fiscal,
            filial, cliente, cidade_entrega, uf_entrega, status, motorista, dias_atraso,
            valor_total, prazo_considerado, status_prazo,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.snapshot_run_id, NEW.business_date, NEW.remessa_numero, NEW.nro_entrega, NEW.nota_fiscal,
            NEW.filial, NEW.cliente, NEW.cidade_entrega, NEW.uf_entrega, NEW.status, NEW.motorista, NEW.dias_atraso,
            NEW.valor_total, NEW.prazo_considerado, NEW.status_prazo,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_bi_snapshot_overdue_audit (
            id, snapshot_run_id, business_date, remessa_numero, nro_entrega, nota_fiscal,
            filial, cliente, cidade_entrega, uf_entrega, status, motorista, dias_atraso,
            valor_total, prazo_considerado, status_prazo,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.snapshot_run_id, NEW.business_date, NEW.remessa_numero, NEW.nro_entrega, NEW.nota_fiscal,
            NEW.filial, NEW.cliente, NEW.cidade_entrega, NEW.uf_entrega, NEW.status, NEW.motorista, NEW.dias_atraso,
            NEW.valor_total, NEW.prazo_considerado, NEW.status_prazo,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_bi_snapshot_overdue_audit (
            id, snapshot_run_id, business_date, remessa_numero, nro_entrega, nota_fiscal,
            filial, cliente, cidade_entrega, uf_entrega, status, motorista, dias_atraso,
            valor_total, prazo_considerado, status_prazo,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            OLD.id, OLD.snapshot_run_id, OLD.business_date, OLD.remessa_numero, OLD.nro_entrega, OLD.nota_fiscal,
            OLD.filial, OLD.cliente, OLD.cidade_entrega, OLD.uf_entrega, OLD.status, OLD.motorista, OLD.dias_atraso,
            OLD.valor_total, OLD.prazo_considerado, OLD.status_prazo,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled, NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_bi_snapshot_overdue_audit ON prb_bi_snapshot_overdue;
CREATE TRIGGER trg_prb_bi_snapshot_overdue_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_bi_snapshot_overdue
FOR EACH ROW
EXECUTE FUNCTION fn_prb_bi_snapshot_overdue_audit();
