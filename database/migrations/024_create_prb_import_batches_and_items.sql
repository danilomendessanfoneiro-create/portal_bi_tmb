-- 024_create_prb_import_batches_and_items.sql

CREATE TABLE IF NOT EXISTS prb_import_batches (
    id                  SERIAL PRIMARY KEY,
    file_name           VARCHAR(500) NOT NULL,
    file_ext            VARCHAR(10) NOT NULL,
    file_size_bytes     BIGINT NOT NULL,
    file_path           TEXT NOT NULL,
    file_mtime          TIMESTAMP WITHOUT TIME ZONE,
    status              VARCHAR(30) NOT NULL DEFAULT 'uploaded',
    total_rows          INTEGER NOT NULL DEFAULT 0,
    valid_rows          INTEGER NOT NULL DEFAULT 0,
    error_rows          INTEGER NOT NULL DEFAULT 0,
    rows_processed      INTEGER NOT NULL DEFAULT 0,
    rows_inserted       INTEGER NOT NULL DEFAULT 0,
    rows_updated        INTEGER NOT NULL DEFAULT 0,
    progress_pct        NUMERIC(5, 2) NOT NULL DEFAULT 0,
    validation_errors   JSONB NOT NULL DEFAULT '[]'::jsonb,
    started_on          TIMESTAMP WITHOUT TIME ZONE,
    finished_on         TIMESTAMP WITHOUT TIME ZONE,
    duration_ms         INTEGER,
    error_message       TEXT,
    report_job_status   VARCHAR(30),
    report_job_message  TEXT,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT ck_prb_import_batches_status CHECK (
        status IN (
            'uploaded',
            'validating',
            'validated_ok',
            'validated_error',
            'importing',
            'imported',
            'failed'
        )
    )
);

CREATE INDEX IF NOT EXISTS ix_prb_import_batches_status ON prb_import_batches (status);
CREATE INDEX IF NOT EXISTS ix_prb_import_batches_created ON prb_import_batches (created_on DESC);
CREATE INDEX IF NOT EXISTS ix_prb_import_batches_file ON prb_import_batches (file_name);
CREATE INDEX IF NOT EXISTS ix_prb_import_batches_actor ON prb_import_batches (created_by);

CREATE TABLE IF NOT EXISTS prb_import_batch_items (
    id                  SERIAL PRIMARY KEY,
    batch_id            INTEGER NOT NULL REFERENCES prb_import_batches (id) ON DELETE CASCADE,
    row_number          INTEGER NOT NULL,
    remessa_numero      VARCHAR(100),
    nro_entrega         VARCHAR(100),
    nota_fiscal         VARCHAR(100),
    cliente             VARCHAR(500),
    filial              VARCHAR(200),
    cidade_entrega      VARCHAR(200),
    uf_entrega          VARCHAR(10),
    status_entrega      VARCHAR(100),
    valor_total         NUMERIC(18, 2),
    qtde_volumes        NUMERIC(18, 4),
    dt_prazo_atual      TIMESTAMP WITHOUT TIME ZONE,
    dt_agendamento      TIMESTAMP WITHOUT TIME ZONE,
    dt_entrega          TIMESTAMP WITHOUT TIME ZONE,
    dt_cancelamento     TIMESTAMP WITHOUT TIME ZONE,
    motivo_cancelamento TEXT,
    motivo_atraso       TEXT,
    nome_recebedor      VARCHAR(500),
    dt_cadastro         TIMESTAMP WITHOUT TIME ZONE,
    motorista           VARCHAR(200),
    remetente           VARCHAR(500),
    cidade_remetente    VARCHAR(200),
    uf_remetente        VARCHAR(10),
    peso_taxado         NUMERIC(18, 4),
    peso_informado      NUMERIC(18, 4),
    payload             JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_valid            BOOLEAN,
    error_message       TEXT,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_prb_import_batch_items_row UNIQUE (batch_id, row_number)
);

CREATE INDEX IF NOT EXISTS ix_prb_import_batch_items_batch ON prb_import_batch_items (batch_id);
CREATE INDEX IF NOT EXISTS ix_prb_import_batch_items_remessa ON prb_import_batch_items (batch_id, remessa_numero);

CREATE TABLE IF NOT EXISTS prb_import_logs (
    id                  SERIAL PRIMARY KEY,
    batch_id            INTEGER NOT NULL REFERENCES prb_import_batches (id) ON DELETE CASCADE,
    row_number          INTEGER,
    level               VARCHAR(20) NOT NULL DEFAULT 'error',
    message             TEXT NOT NULL,
    created_by          VARCHAR(100),
    created_on          TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    modified_by         VARCHAR(100),
    modified_on         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT ck_prb_import_logs_level CHECK (level IN ('info', 'warning', 'error'))
);

CREATE INDEX IF NOT EXISTS ix_prb_import_logs_batch ON prb_import_logs (batch_id, id);
