-- 028_add_dt_recebimento.sql
-- Persiste Dt. Recebimento da planilha/API (campo distinto de Dt. Entrega)

ALTER TABLE prb_deliveries
    ADD COLUMN IF NOT EXISTS dt_recebimento TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE prb_deliveries_audit
    ADD COLUMN IF NOT EXISTS dt_recebimento TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE prb_import_batch_items
    ADD COLUMN IF NOT EXISTS dt_recebimento TIMESTAMP WITHOUT TIME ZONE;

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
            created_by, created_on, modified_by, modified_on, enabled, dt_recebimento, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.remessa_numero, NEW.nro_entrega, NEW.nota_fiscal, NEW.cliente, NEW.filial, NEW.cidade_entrega, NEW.uf_entrega,
            NEW.status, NEW.valor_total, NEW.qtde_volumes, NEW.dt_prazo_atual, NEW.dt_agendamento, NEW.dt_entrega, NEW.dt_cancelamento,
            NEW.motivo_cancelamento, NEW.motivo_atraso, NEW.nome_recebedor, NEW.dt_cadastro, NEW.motorista, NEW.remetente,
            NEW.cidade_remetente, NEW.uf_remetente, NEW.peso_taxado, NEW.peso_informado, NEW.raw_json, NEW.synced_at, NEW.source,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NEW.dt_recebimento, NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_deliveries_audit (
            id, remessa_numero, nro_entrega, nota_fiscal, cliente, filial, cidade_entrega, uf_entrega,
            status, valor_total, qtde_volumes, dt_prazo_atual, dt_agendamento, dt_entrega, dt_cancelamento,
            motivo_cancelamento, motivo_atraso, nome_recebedor, dt_cadastro, motorista, remetente,
            cidade_remetente, uf_remetente, peso_taxado, peso_informado, raw_json, synced_at, source,
            created_by, created_on, modified_by, modified_on, enabled, dt_recebimento, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.remessa_numero, NEW.nro_entrega, NEW.nota_fiscal, NEW.cliente, NEW.filial, NEW.cidade_entrega, NEW.uf_entrega,
            NEW.status, NEW.valor_total, NEW.qtde_volumes, NEW.dt_prazo_atual, NEW.dt_agendamento, NEW.dt_entrega, NEW.dt_cancelamento,
            NEW.motivo_cancelamento, NEW.motivo_atraso, NEW.nome_recebedor, NEW.dt_cadastro, NEW.motorista, NEW.remetente,
            NEW.cidade_remetente, NEW.uf_remetente, NEW.peso_taxado, NEW.peso_informado, NEW.raw_json, NEW.synced_at, NEW.source,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NEW.dt_recebimento, NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_deliveries_audit (
            id, remessa_numero, nro_entrega, nota_fiscal, cliente, filial, cidade_entrega, uf_entrega,
            status, valor_total, qtde_volumes, dt_prazo_atual, dt_agendamento, dt_entrega, dt_cancelamento,
            motivo_cancelamento, motivo_atraso, nome_recebedor, dt_cadastro, motorista, remetente,
            cidade_remetente, uf_remetente, peso_taxado, peso_informado, raw_json, synced_at, source,
            created_by, created_on, modified_by, modified_on, enabled, dt_recebimento, created_on_audit, action
        ) VALUES (
            OLD.id, OLD.remessa_numero, OLD.nro_entrega, OLD.nota_fiscal, OLD.cliente, OLD.filial, OLD.cidade_entrega, OLD.uf_entrega,
            OLD.status, OLD.valor_total, OLD.qtde_volumes, OLD.dt_prazo_atual, OLD.dt_agendamento, OLD.dt_entrega, OLD.dt_cancelamento,
            OLD.motivo_cancelamento, OLD.motivo_atraso, OLD.nome_recebedor, OLD.dt_cadastro, OLD.motorista, OLD.remetente,
            OLD.cidade_remetente, OLD.uf_remetente, OLD.peso_taxado, OLD.peso_informado, OLD.raw_json, OLD.synced_at, OLD.source,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled, OLD.dt_recebimento, NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;
