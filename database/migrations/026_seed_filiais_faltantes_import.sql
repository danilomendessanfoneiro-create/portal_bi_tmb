-- 026_seed_filiais_faltantes_import.sql
-- Cadastro das filiais ausentes na validação de importação manual.
-- Preferível: database/deploy/seed_filiais_faltantes_import.py (gera hash com o salt do .env).
-- Este SQL só funciona se password_hash abaixo for regenerado para o ambiente.
--
-- Filiais: TMB ARARUAMA, TMB DIVINOPOLIS, TMB UBERLÂNDIA, TMB MACHADO,
--          TMB JUIZ DE FORA, TMB VALADARES

INSERT INTO prb_users (
    login, password_hash, profile, branch, display_name, name, code,
    created_by, created_on, modified_by, modified_on, enabled
)
SELECT v.login, v.password_hash, 'filial', v.branch, v.display_name, v.name, v.code,
       'seed_filiais_faltantes', NOW(), 'seed_filiais_faltantes', NOW(), TRUE
FROM (
    VALUES
        ('araruama',    'REPLACE_WITH_HASH', 'TMB ARARUAMA',      'TMB Araruama',      'TMB Araruama',      'araruama'),
        ('divinopolis', 'REPLACE_WITH_HASH', 'TMB DIVINOPOLIS',   'TMB Divinópolis',   'TMB Divinópolis',   'divinopolis'),
        ('uberlandia',  'REPLACE_WITH_HASH', 'TMB UBERLÂNDIA',    'TMB Uberlândia',    'TMB Uberlândia',    'uberlandia'),
        ('machado',     'REPLACE_WITH_HASH', 'TMB MACHADO',       'TMB Machado',       'TMB Machado',       'machado'),
        ('juizdefora',  'REPLACE_WITH_HASH', 'TMB JUIZ DE FORA',  'TMB Juiz de Fora',  'TMB Juiz de Fora',  'juizdefora'),
        ('valadares',   'REPLACE_WITH_HASH', 'TMB VALADARES',     'TMB Valadares',     'TMB Valadares',     'valadares')
) AS v(login, password_hash, branch, display_name, name, code)
WHERE NOT EXISTS (
    SELECT 1 FROM prb_users u
    WHERE lower(u.profile) = 'filial'
      AND u.enabled = TRUE
      AND TRIM(u.branch) = v.branch
)
ON CONFLICT (login) DO UPDATE SET
    profile = 'filial',
    branch = EXCLUDED.branch,
    display_name = EXCLUDED.display_name,
    name = EXCLUDED.name,
    enabled = TRUE,
    modified_by = 'seed_filiais_faltantes',
    modified_on = NOW();
