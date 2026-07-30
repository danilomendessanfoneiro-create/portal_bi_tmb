-- 016_create_prb_deliveries.sql

CREATE TABLE IF NOT EXISTS prb_deliveries (
    id                  SERIAL PRIMARY KEY,
    remessa_numero      VARCHAR(100) NOT NULL,
    nro_entrega         VARCHAR(100) NOT NULL,
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
    synced_at           TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    source              VARCHAR(40) NOT NULL DEFAULT 'api',
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_prb_deliveries_remessa UNIQUE (remessa_numero)
);

CREATE INDEX IF NOT EXISTS ix_prb_deliveries_filial ON prb_deliveries (filial);
CREATE INDEX IF NOT EXISTS ix_prb_deliveries_dt_cadastro ON prb_deliveries (dt_cadastro);
CREATE INDEX IF NOT EXISTS ix_prb_deliveries_enabled ON prb_deliveries (enabled);
CREATE INDEX IF NOT EXISTS ix_prb_deliveries_nro ON prb_deliveries (nro_entrega);
