-- 047_create_prb_import_auto_branches.sql
-- Filiais criadas automaticamente durante validate de importação (auditoria por lote).

CREATE TABLE IF NOT EXISTS prb_import_auto_branches (
    id              SERIAL PRIMARY KEY,
    batch_id        INTEGER NOT NULL REFERENCES prb_import_batches (id) ON DELETE CASCADE,
    user_id         INTEGER REFERENCES prb_users (id) ON DELETE SET NULL,
    branch          VARCHAR(200) NOT NULL,
    login           VARCHAR(100) NOT NULL,
    created_by      VARCHAR(100),
    created_on      TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_prb_import_auto_branches_batch_branch UNIQUE (batch_id, branch)
);

CREATE INDEX IF NOT EXISTS ix_prb_import_auto_branches_batch
    ON prb_import_auto_branches (batch_id);

CREATE INDEX IF NOT EXISTS ix_prb_import_auto_branches_branch
    ON prb_import_auto_branches (branch);
