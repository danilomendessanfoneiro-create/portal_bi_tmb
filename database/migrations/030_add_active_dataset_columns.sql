-- 030_add_active_dataset_columns.sql
-- Marca cada entrega com o lote (planilha ou sync API) para filtrar a análise BI.

ALTER TABLE prb_deliveries
    ADD COLUMN IF NOT EXISTS dataset_source VARCHAR(40),
    ADD COLUMN IF NOT EXISTS dataset_batch_id INTEGER,
    ADD COLUMN IF NOT EXISTS dataset_sync_id INTEGER;

ALTER TABLE prb_deliveries_audit
    ADD COLUMN IF NOT EXISTS dataset_source VARCHAR(40),
    ADD COLUMN IF NOT EXISTS dataset_batch_id INTEGER,
    ADD COLUMN IF NOT EXISTS dataset_sync_id INTEGER;

CREATE INDEX IF NOT EXISTS ix_prb_deliveries_dataset_batch
    ON prb_deliveries (dataset_batch_id)
    WHERE enabled = TRUE AND dataset_batch_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_prb_deliveries_dataset_sync
    ON prb_deliveries (dataset_sync_id)
    WHERE enabled = TRUE AND dataset_sync_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS prb_active_dataset (
    id                  SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    source              VARCHAR(40) NOT NULL,
    batch_id            INTEGER,
    sync_id             INTEGER,
    label               VARCHAR(500),
    activated_on        TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    row_count           INTEGER,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT ck_prb_active_dataset_source CHECK (source IN ('manual_import', 'api_sync'))
);

CREATE OR REPLACE FUNCTION fn_prb_deliveries_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO prb_deliveries_audit (
            id, remessa_numero, nro_entrega, nota_fiscal, cliente, filial, cidade_entrega, uf_entrega,
            status, valor_total, qtde_volumes, dt_prazo_atual, dt_agendamento, dt_entrega, dt_cancelamento,
            motivo_cancelamento, motivo_atraso, nome_recebedor, dt_cadastro, motorista, remetente,
            cidade_remetente, uf_remetente, peso_taxado, peso_informado, raw_json, synced_at, source,
            created_by, created_on, modified_by, modified_on, enabled, dt_recebimento, cliente_conta,
            dataset_source, dataset_batch_id, dataset_sync_id, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.remessa_numero, NEW.nro_entrega, NEW.nota_fiscal, NEW.cliente, NEW.filial, NEW.cidade_entrega, NEW.uf_entrega,
            NEW.status, NEW.valor_total, NEW.qtde_volumes, NEW.dt_prazo_atual, NEW.dt_agendamento, NEW.dt_entrega, NEW.dt_cancelamento,
            NEW.motivo_cancelamento, NEW.motivo_atraso, NEW.nome_recebedor, NEW.dt_cadastro, NEW.motorista, NEW.remetente,
            NEW.cidade_remetente, NEW.uf_remetente, NEW.peso_taxado, NEW.peso_informado, NEW.raw_json, NEW.synced_at, NEW.source,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NEW.dt_recebimento, NEW.cliente_conta,
            NEW.dataset_source, NEW.dataset_batch_id, NEW.dataset_sync_id, NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_deliveries_audit (
            id, remessa_numero, nro_entrega, nota_fiscal, cliente, filial, cidade_entrega, uf_entrega,
            status, valor_total, qtde_volumes, dt_prazo_atual, dt_agendamento, dt_entrega, dt_cancelamento,
            motivo_cancelamento, motivo_atraso, nome_recebedor, dt_cadastro, motorista, remetente,
            cidade_remetente, uf_remetente, peso_taxado, peso_informado, raw_json, synced_at, source,
            created_by, created_on, modified_by, modified_on, enabled, dt_recebimento, cliente_conta,
            dataset_source, dataset_batch_id, dataset_sync_id, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.remessa_numero, NEW.nro_entrega, NEW.nota_fiscal, NEW.cliente, NEW.filial, NEW.cidade_entrega, NEW.uf_entrega,
            NEW.status, NEW.valor_total, NEW.qtde_volumes, NEW.dt_prazo_atual, NEW.dt_agendamento, NEW.dt_entrega, NEW.dt_cancelamento,
            NEW.motivo_cancelamento, NEW.motivo_atraso, NEW.nome_recebedor, NEW.dt_cadastro, NEW.motorista, NEW.remetente,
            NEW.cidade_remetente, NEW.uf_remetente, NEW.peso_taxado, NEW.peso_informado, NEW.raw_json, NEW.synced_at, NEW.source,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NEW.dt_recebimento, NEW.cliente_conta,
            NEW.dataset_source, NEW.dataset_batch_id, NEW.dataset_sync_id, NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_deliveries_audit (
            id, remessa_numero, nro_entrega, nota_fiscal, cliente, filial, cidade_entrega, uf_entrega,
            status, valor_total, qtde_volumes, dt_prazo_atual, dt_agendamento, dt_entrega, dt_cancelamento,
            motivo_cancelamento, motivo_atraso, nome_recebedor, dt_cadastro, motorista, remetente,
            cidade_remetente, uf_remetente, peso_taxado, peso_informado, raw_json, synced_at, source,
            created_by, created_on, modified_by, modified_on, enabled, dt_recebimento, cliente_conta,
            dataset_source, dataset_batch_id, dataset_sync_id, created_on_audit, action
        ) VALUES (
            OLD.id, OLD.remessa_numero, OLD.nro_entrega, OLD.nota_fiscal, OLD.cliente, OLD.filial, OLD.cidade_entrega, OLD.uf_entrega,
            OLD.status, OLD.valor_total, OLD.qtde_volumes, OLD.dt_prazo_atual, OLD.dt_agendamento, OLD.dt_entrega, OLD.dt_cancelamento,
            OLD.motivo_cancelamento, OLD.motivo_atraso, OLD.nome_recebedor, OLD.dt_cadastro, OLD.motorista, OLD.remetente,
            OLD.cidade_remetente, OLD.uf_remetente, OLD.peso_taxado, OLD.peso_informado, OLD.raw_json, OLD.synced_at, OLD.source,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled, OLD.dt_recebimento, OLD.cliente_conta,
            OLD.dataset_source, OLD.dataset_batch_id, OLD.dataset_sync_id, NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;
