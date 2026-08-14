-- 043_rename_tms_import_and_show_api_disabled.sql
-- Renomeia coleta TMS para "Importação de pedidos", ativa esse job
-- e reforça jobs de API desabilitados (visíveis na UI, sem executar).

UPDATE prb_job_settings
SET display_name = 'Importação de pedidos',
    enabled = TRUE,
    modified_by = 'seed',
    modified_on = NOW()
WHERE job_id = 'fetch_tmselite_spreadsheet';

UPDATE prb_job_settings
SET display_name = COALESCE(NULLIF(TRIM(display_name), ''), 'Atualização Diária (API Entregas)'),
    enabled = FALSE,
    modified_by = 'seed',
    modified_on = NOW()
WHERE job_id = 'import_deliveries_daily';

UPDATE prb_job_settings
SET display_name = COALESCE(NULLIF(TRIM(display_name), ''), 'Migração Inicial (API Entregas)'),
    enabled = FALSE,
    modified_by = 'seed',
    modified_on = NOW()
WHERE job_id = 'import_deliveries_initial';
