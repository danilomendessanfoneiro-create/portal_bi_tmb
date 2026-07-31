-- 027_extend_prb_bi_snapshot_run_source.sql
-- Permite origem manual_import além de job / seed-demo

ALTER TABLE prb_bi_snapshot_run
    DROP CONSTRAINT IF EXISTS ck_prb_bi_snapshot_run_source;

ALTER TABLE prb_bi_snapshot_run
    ADD CONSTRAINT ck_prb_bi_snapshot_run_source
    CHECK (source IN ('job', 'seed-demo', 'manual_import'));
