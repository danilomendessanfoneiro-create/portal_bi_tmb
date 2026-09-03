-- 046_add_snapshot_cliente_conta.sql
-- Cliente indústria (planilha "Cliente" / embarcador) nos snapshots do BI.

ALTER TABLE prb_bi_snapshot_overdue
    ADD COLUMN IF NOT EXISTS cliente_conta VARCHAR(500);

ALTER TABLE prb_bi_snapshot_overdue_audit
    ADD COLUMN IF NOT EXISTS cliente_conta VARCHAR(500);

ALTER TABLE prb_progress_snapshot_item
    ADD COLUMN IF NOT EXISTS cliente_conta VARCHAR(500);

ALTER TABLE prb_progress_snapshot_item_audit
    ADD COLUMN IF NOT EXISTS cliente_conta VARCHAR(500);

CREATE INDEX IF NOT EXISTS ix_prb_bi_snapshot_overdue_cliente_conta
    ON prb_bi_snapshot_overdue (cliente_conta, business_date)
    WHERE cliente_conta IS NOT NULL AND enabled = TRUE;

CREATE INDEX IF NOT EXISTS ix_prb_progress_snapshot_item_cliente_conta
    ON prb_progress_snapshot_item (cliente_conta)
    WHERE cliente_conta IS NOT NULL AND enabled = TRUE;

UPDATE prb_bi_snapshot_overdue o
SET cliente_conta = d.cliente_conta
FROM prb_deliveries d
WHERE o.enabled = TRUE
  AND d.enabled = TRUE
  AND o.nro_entrega IS NOT NULL
  AND o.nro_entrega = d.nro_entrega
  AND d.cliente_conta IS NOT NULL
  AND NULLIF(BTRIM(d.cliente_conta), '') IS NOT NULL
  AND o.cliente_conta IS NULL;

UPDATE prb_progress_snapshot_item i
SET cliente_conta = d.cliente_conta
FROM prb_deliveries d
WHERE i.enabled = TRUE
  AND d.enabled = TRUE
  AND i.nro_entrega IS NOT NULL
  AND i.nro_entrega = d.nro_entrega
  AND d.cliente_conta IS NOT NULL
  AND NULLIF(BTRIM(d.cliente_conta), '') IS NOT NULL
  AND i.cliente_conta IS NULL;

CREATE OR REPLACE FUNCTION fn_prb_bi_snapshot_overdue_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_bi_snapshot_overdue_audit (
            id, snapshot_run_id, business_date, remessa_numero, nro_entrega, nota_fiscal,
            filial, cliente, cliente_conta, cidade_entrega, uf_entrega, status, motorista, dias_atraso,
            valor_total, prazo_considerado, status_prazo,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.snapshot_run_id, NEW.business_date, NEW.remessa_numero, NEW.nro_entrega, NEW.nota_fiscal,
            NEW.filial, NEW.cliente, NEW.cliente_conta, NEW.cidade_entrega, NEW.uf_entrega, NEW.status, NEW.motorista, NEW.dias_atraso,
            NEW.valor_total, NEW.prazo_considerado, NEW.status_prazo,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_bi_snapshot_overdue_audit (
            id, snapshot_run_id, business_date, remessa_numero, nro_entrega, nota_fiscal,
            filial, cliente, cliente_conta, cidade_entrega, uf_entrega, status, motorista, dias_atraso,
            valor_total, prazo_considerado, status_prazo,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.snapshot_run_id, NEW.business_date, NEW.remessa_numero, NEW.nro_entrega, NEW.nota_fiscal,
            NEW.filial, NEW.cliente, NEW.cliente_conta, NEW.cidade_entrega, NEW.uf_entrega, NEW.status, NEW.motorista, NEW.dias_atraso,
            NEW.valor_total, NEW.prazo_considerado, NEW.status_prazo,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_bi_snapshot_overdue_audit (
            id, snapshot_run_id, business_date, remessa_numero, nro_entrega, nota_fiscal,
            filial, cliente, cliente_conta, cidade_entrega, uf_entrega, status, motorista, dias_atraso,
            valor_total, prazo_considerado, status_prazo,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            OLD.id, OLD.snapshot_run_id, OLD.business_date, OLD.remessa_numero, OLD.nro_entrega, OLD.nota_fiscal,
            OLD.filial, OLD.cliente, OLD.cliente_conta, OLD.cidade_entrega, OLD.uf_entrega, OLD.status, OLD.motorista, OLD.dias_atraso,
            OLD.valor_total, OLD.prazo_considerado, OLD.status_prazo,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled, NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION fn_prb_progress_snapshot_item_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_progress_snapshot_item_audit (
            id, snapshot_run_id, nro_entrega, remessa_numero, status, status_prazo,
            filial, cliente, cliente_conta, cnpj_cliente,
            cidade_entrega, uf_entrega, motorista, valor_total,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.snapshot_run_id, NEW.nro_entrega, NEW.remessa_numero, NEW.status, NEW.status_prazo,
            NEW.filial, NEW.cliente, NEW.cliente_conta, NEW.cnpj_cliente,
            NEW.cidade_entrega, NEW.uf_entrega, NEW.motorista, NEW.valor_total,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_progress_snapshot_item_audit (
            id, snapshot_run_id, nro_entrega, remessa_numero, status, status_prazo,
            filial, cliente, cliente_conta, cnpj_cliente,
            cidade_entrega, uf_entrega, motorista, valor_total,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.snapshot_run_id, NEW.nro_entrega, NEW.remessa_numero, NEW.status, NEW.status_prazo,
            NEW.filial, NEW.cliente, NEW.cliente_conta, NEW.cnpj_cliente,
            NEW.cidade_entrega, NEW.uf_entrega, NEW.motorista, NEW.valor_total,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_progress_snapshot_item_audit (
            id, snapshot_run_id, nro_entrega, remessa_numero, status, status_prazo,
            filial, cliente, cliente_conta, cnpj_cliente,
            cidade_entrega, uf_entrega, motorista, valor_total,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            OLD.id, OLD.snapshot_run_id, OLD.nro_entrega, OLD.remessa_numero, OLD.status, OLD.status_prazo,
            OLD.filial, OLD.cliente, OLD.cliente_conta, OLD.cnpj_cliente,
            OLD.cidade_entrega, OLD.uf_entrega, OLD.motorista, OLD.valor_total,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled, NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;
