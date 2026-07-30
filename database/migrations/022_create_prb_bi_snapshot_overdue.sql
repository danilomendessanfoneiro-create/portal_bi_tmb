-- 022_create_prb_bi_snapshot_overdue.sql

CREATE TABLE IF NOT EXISTS prb_bi_snapshot_overdue (
    id                  SERIAL PRIMARY KEY,
    snapshot_run_id     INTEGER NOT NULL REFERENCES prb_bi_snapshot_run (id) ON DELETE CASCADE,
    business_date       DATE NOT NULL,
    remessa_numero      VARCHAR(100) NOT NULL,
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
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_prb_bi_snapshot_overdue_run_remessa UNIQUE (snapshot_run_id, remessa_numero)
);

CREATE INDEX IF NOT EXISTS ix_prb_bi_snapshot_overdue_date
    ON prb_bi_snapshot_overdue (business_date);

CREATE INDEX IF NOT EXISTS ix_prb_bi_snapshot_overdue_filial_date
    ON prb_bi_snapshot_overdue (filial, business_date);

CREATE INDEX IF NOT EXISTS ix_prb_bi_snapshot_overdue_cliente_date
    ON prb_bi_snapshot_overdue (cliente, business_date);

CREATE INDEX IF NOT EXISTS ix_prb_bi_snapshot_overdue_cidade_date
    ON prb_bi_snapshot_overdue (cidade_entrega, business_date);
