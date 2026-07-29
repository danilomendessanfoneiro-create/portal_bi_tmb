-- 003_seed_prb_users.sql
-- Initial users from legacy usuarios.csv (password hashes preserved)

INSERT INTO prb_users (
    login, password_hash, profile, branch, display_name, name, code,
    created_by, created_on, modified_by, modified_on, enabled
)
VALUES
(
    'admin',
    'f7aea6c935bb741fd19350c0886cfe1669a62b109ce32e2a19e435cafddfaee8',
    'admin', 'TODAS', 'Gestão TMB', 'Gestão TMB', 'admin',
    'system', NOW(), 'system', NOW(), TRUE
),
(
    'dcaxias',
    '901d951a9d05075041ef75513277225baaa0566da5e69dc2882f4053e1bdec32',
    'filial', 'TMB D. DE CAXIAS', 'TMB D. de Caxias', 'TMB D. de Caxias', 'dcaxias',
    'system', NOW(), 'system', NOW(), TRUE
),
(
    'viana',
    '901d951a9d05075041ef75513277225baaa0566da5e69dc2882f4053e1bdec32',
    'filial', 'TMB VIANA', 'TMB Viana', 'TMB Viana', 'viana',
    'system', NOW(), 'system', NOW(), TRUE
),
(
    'patosdeminas',
    '901d951a9d05075041ef75513277225baaa0566da5e69dc2882f4053e1bdec32',
    'filial', 'TMB PATOS DE MINAS', 'TMB Patos de Minas', 'TMB Patos de Minas', 'patosdeminas',
    'system', NOW(), 'system', NOW(), TRUE
),
(
    'tocantins',
    '901d951a9d05075041ef75513277225baaa0566da5e69dc2882f4053e1bdec32',
    'filial', 'TMB TOCANTINS', 'TMB Tocantins', 'TMB Tocantins', 'tocantins',
    'system', NOW(), 'system', NOW(), TRUE
),
(
    'montesclaros',
    '901d951a9d05075041ef75513277225baaa0566da5e69dc2882f4053e1bdec32',
    'filial', 'TMB MONTES CLAROS', 'TMB Montes Claros', 'TMB Montes Claros', 'montesclaros',
    'system', NOW(), 'system', NOW(), TRUE
),
(
    'betim',
    '901d951a9d05075041ef75513277225baaa0566da5e69dc2882f4053e1bdec32',
    'filial', 'TMB BETIM', 'TMB Betim', 'TMB Betim', 'betim',
    'system', NOW(), 'system', NOW(), TRUE
),
(
    'saofidelis',
    '901d951a9d05075041ef75513277225baaa0566da5e69dc2882f4053e1bdec32',
    'filial', 'TMB SAO FIDELIS', 'TMB São Fidélis', 'TMB São Fidélis', 'saofidelis',
    'system', NOW(), 'system', NOW(), TRUE
),
(
    'varginha',
    '901d951a9d05075041ef75513277225baaa0566da5e69dc2882f4053e1bdec32',
    'filial', 'TMB VARGINHA', 'TMB Varginha', 'TMB Varginha', 'varginha',
    'system', NOW(), 'system', NOW(), TRUE
)
ON CONFLICT (login) DO NOTHING;
