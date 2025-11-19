-- Script para testar a inserção manual de dados ITAD
-- Use para validar a estrutura das tabelas itad_raw e steam_itad_mapping

-- 1. Verificar estrutura das tabelas
\d itad_raw
\d steam_itad_mapping

-- 2. Inserção de teste no itad_raw (para CS:GO - appid real)
INSERT INTO itad_raw (id_itad, slug, title, type, mature, assets, ultima_atualizacao)
VALUES (
    'app/730',
    'counter-strike-global-offensive',
    'Counter-Strike: Global Offensive',
    'game',
    false,
    '{"banner": "https://example.com/csgo.jpg"}'::jsonb,
    NOW()
)
ON CONFLICT (id_itad) 
DO UPDATE SET
    slug = EXCLUDED.slug,
    title = EXCLUDED.title,
    ultima_atualizacao = EXCLUDED.ultima_atualizacao;

-- 3. Inserção de teste no steam_itad_mapping
-- (CS:GO - AppID 730 existe em steam_generico)
INSERT INTO steam_itad_mapping (appid, id_itad, slug, title)
VALUES (
    730,  -- Counter-Strike: Global Offensive (AppID real)
    'app/730',
    'counter-strike-global-offensive',
    'Counter-Strike: Global Offensive'
)
ON CONFLICT (appid)
DO UPDATE SET
    id_itad = EXCLUDED.id_itad,
    slug = EXCLUDED.slug,
    title = EXCLUDED.title;

-- 4. Verificar dados inseridos
SELECT * FROM itad_raw WHERE id_itad IN ('app/123456', 'app/730');
SELECT * FROM steam_itad_mapping WHERE appid IN (123456, 730);

-- 5. Testar JOIN completo
SELECT 
    sb.appid,
    sb.nome,
    sim.id_itad,
    ir.slug,
    ir.title,
    ir.ultima_atualizacao
FROM steam_bd sb
JOIN steam_itad_mapping sim ON sb.appid = sim.appid
JOIN itad_raw ir ON sim.id_itad = ir.id_itad
WHERE sb.appid = 730;

-- 6. Limpar dados de teste (opcional)
-- DELETE FROM steam_itad_mapping WHERE appid = 123456;
-- DELETE FROM itad_raw WHERE id_itad = 'app/123456';
