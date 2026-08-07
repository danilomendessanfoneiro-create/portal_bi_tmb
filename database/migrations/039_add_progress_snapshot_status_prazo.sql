-- 039_add_progress_snapshot_status_prazo.sql
-- STATUS PRAZO (calcConsolidada) na Progressão.

ALTER TABLE prb_progress_snapshot_item
    ADD COLUMN IF NOT EXISTS status_prazo VARCHAR(40);

ALTER TABLE prb_progress_snapshot_item_audit
    ADD COLUMN IF NOT EXISTS status_prazo VARCHAR(40);

CREATE INDEX IF NOT EXISTS ix_prb_progress_snapshot_item_status_prazo
    ON prb_progress_snapshot_item (status_prazo);

CREATE OR REPLACE FUNCTION fn_prb_progress_snapshot_item_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_progress_snapshot_item_audit (
            id, snapshot_run_id, nro_entrega, remessa_numero, status, status_prazo,
            filial, cliente, cnpj_cliente,
            cidade_entrega, uf_entrega, motorista, valor_total,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.snapshot_run_id, NEW.nro_entrega, NEW.remessa_numero, NEW.status, NEW.status_prazo,
            NEW.filial, NEW.cliente, NEW.cnpj_cliente,
            NEW.cidade_entrega, NEW.uf_entrega, NEW.motorista, NEW.valor_total,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_progress_snapshot_item_audit (
            id, snapshot_run_id, nro_entrega, remessa_numero, status, status_prazo,
            filial, cliente, cnpj_cliente,
            cidade_entrega, uf_entrega, motorista, valor_total,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.snapshot_run_id, NEW.nro_entrega, NEW.remessa_numero, NEW.status, NEW.status_prazo,
            NEW.filial, NEW.cliente, NEW.cnpj_cliente,
            NEW.cidade_entrega, NEW.uf_entrega, NEW.motorista, NEW.valor_total,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_progress_snapshot_item_audit (
            id, snapshot_run_id, nro_entrega, remessa_numero, status, status_prazo,
            filial, cliente, cnpj_cliente,
            cidade_entrega, uf_entrega, motorista, valor_total,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            OLD.id, OLD.snapshot_run_id, OLD.nro_entrega, OLD.remessa_numero, OLD.status, OLD.status_prazo,
            OLD.filial, OLD.cliente, OLD.cnpj_cliente,
            OLD.cidade_entrega, OLD.uf_entrega, OLD.motorista, OLD.valor_total,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled, NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;
