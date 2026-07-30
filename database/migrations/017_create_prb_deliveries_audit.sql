-- 017_create_prb_deliveries_audit.sql

CREATE TABLE IF NOT EXISTS prb_deliveries_audit (
    id                  INTEGER,
    remessa_numero      VARCHAR(100),
    nro_entrega         VARCHAR(100),
    nota_fiscal         VARCHAR(100),
    cliente             VARCHAR(500),
    filial              VARCHAR(200),
    cidade_entrega      VARCHAR(200),
    uf_entrega          VARCHAR(10),
    status              VARCHAR(100),
    valor_total         NUMERIC(18, 2),
    qtde_volumes        NUMERIC(18, 2),
    dt_prazo_atual      TIMESTAMP WITHOUT TIME ZONE,
    dt_agendamento      TIMESTAMP WITHOUT TIME ZONE,
    dt_entrega          TIMESTAMP WITHOUT TIME ZONE,
    dt_cancelamento     TIMESTAMP WITHOUT TIME ZONE,
    motivo_cancelamento TEXT,
    motivo_atraso       TEXT,
    nome_recebedor      VARCHAR(300),
    dt_cadastro         TIMESTAMP WITHOUT TIME ZONE,
    motorista           VARCHAR(300),
    remetente           VARCHAR(500),
    cidade_remetente    VARCHAR(200),
    uf_remetente        VARCHAR(10),
    peso_taxado         NUMERIC(18, 4),
    peso_informado      NUMERIC(18, 4),
    raw_json            JSONB,
    synced_at           TIMESTAMP WITHOUT TIME ZONE,
    source              VARCHAR(40),
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE,
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE,
    enabled             BOOLEAN,
    created_on_audit    TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    action              VARCHAR(10) NOT NULL,
    CONSTRAINT ck_prb_deliveries_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX IF NOT EXISTS ix_prb_deliveries_audit_created
    ON prb_deliveries_audit (created_on_audit);

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
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.remessa_numero, NEW.nro_entrega, NEW.nota_fiscal, NEW.cliente, NEW.filial, NEW.cidade_entrega, NEW.uf_entrega,
            NEW.status, NEW.valor_total, NEW.qtde_volumes, NEW.dt_prazo_atual, NEW.dt_agendamento, NEW.dt_entrega, NEW.dt_cancelamento,
            NEW.motivo_cancelamento, NEW.motivo_atraso, NEW.nome_recebedor, NEW.dt_cadastro, NEW.motorista, NEW.remetente,
            NEW.cidade_remetente, NEW.uf_remetente, NEW.peso_taxado, NEW.peso_informado, NEW.raw_json, NEW.synced_at, NEW.source,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'INSERT'
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO prb_deliveries_audit (
            id, remessa_numero, nro_entrega, nota_fiscal, cliente, filial, cidade_entrega, uf_entrega,
            status, valor_total, qtde_volumes, dt_prazo_atual, dt_agendamento, dt_entrega, dt_cancelamento,
            motivo_cancelamento, motivo_atraso, nome_recebedor, dt_cadastro, motorista, remetente,
            cidade_remetente, uf_remetente, peso_taxado, peso_informado, raw_json, synced_at, source,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            NEW.id, NEW.remessa_numero, NEW.nro_entrega, NEW.nota_fiscal, NEW.cliente, NEW.filial, NEW.cidade_entrega, NEW.uf_entrega,
            NEW.status, NEW.valor_total, NEW.qtde_volumes, NEW.dt_prazo_atual, NEW.dt_agendamento, NEW.dt_entrega, NEW.dt_cancelamento,
            NEW.motivo_cancelamento, NEW.motivo_atraso, NEW.nome_recebedor, NEW.dt_cadastro, NEW.motorista, NEW.remetente,
            NEW.cidade_remetente, NEW.uf_remetente, NEW.peso_taxado, NEW.peso_informado, NEW.raw_json, NEW.synced_at, NEW.source,
            NEW.created_by, NEW.created_on, NEW.modified_by, NEW.modified_on, NEW.enabled, NOW(), 'UPDATE'
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO prb_deliveries_audit (
            id, remessa_numero, nro_entrega, nota_fiscal, cliente, filial, cidade_entrega, uf_entrega,
            status, valor_total, qtde_volumes, dt_prazo_atual, dt_agendamento, dt_entrega, dt_cancelamento,
            motivo_cancelamento, motivo_atraso, nome_recebedor, dt_cadastro, motorista, remetente,
            cidade_remetente, uf_remetente, peso_taxado, peso_informado, raw_json, synced_at, source,
            created_by, created_on, modified_by, modified_on, enabled, created_on_audit, action
        ) VALUES (
            OLD.id, OLD.remessa_numero, OLD.nro_entrega, OLD.nota_fiscal, OLD.cliente, OLD.filial, OLD.cidade_entrega, OLD.uf_entrega,
            OLD.status, OLD.valor_total, OLD.qtde_volumes, OLD.dt_prazo_atual, OLD.dt_agendamento, OLD.dt_entrega, OLD.dt_cancelamento,
            OLD.motivo_cancelamento, OLD.motivo_atraso, OLD.nome_recebedor, OLD.dt_cadastro, OLD.motorista, OLD.remetente,
            OLD.cidade_remetente, OLD.uf_remetente, OLD.peso_taxado, OLD.peso_informado, OLD.raw_json, OLD.synced_at, OLD.source,
            OLD.created_by, OLD.created_on, OLD.modified_by, OLD.modified_on, OLD.enabled, NOW(), 'DELETE'
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_prb_deliveries_audit ON prb_deliveries;
CREATE TRIGGER trg_prb_deliveries_audit
AFTER INSERT OR UPDATE OR DELETE ON prb_deliveries
FOR EACH ROW
EXECUTE FUNCTION fn_prb_deliveries_audit();
