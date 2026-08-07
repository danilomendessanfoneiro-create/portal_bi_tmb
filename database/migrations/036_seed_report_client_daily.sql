-- 036_seed_report_client_daily.sql
-- Automação irmã da fase filiais: relatório diário por Cliente (CNPJ).

INSERT INTO prb_job_settings (
    job_id, local_time, timezone, enabled,
    display_name, frequency, weekday, day_of_month,
    created_by, modified_by
)
VALUES (
    'report_client_daily', '07:00', 'America/Sao_Paulo', TRUE,
    'Envio Diário de Relatórios dos Clientes', 'daily', NULL, NULL,
    'seed', 'seed'
)
ON CONFLICT (job_id) DO UPDATE SET
    display_name = COALESCE(prb_job_settings.display_name, EXCLUDED.display_name),
    frequency = COALESCE(NULLIF(prb_job_settings.frequency, ''), EXCLUDED.frequency);
