-- Script para corrigir linguagens corrompidas no steam_bd
-- Executa substituições em massa usando UPDATE com array_replace

UPDATE steam_bd
SET linguagens = (
    SELECT ARRAY_AGG(lang_corrigido)
    FROM (
        SELECT DISTINCT
            CASE 
                WHEN lang = 'Ingl??s' THEN 'Ingles'
                WHEN lang = 'Portugu??s' THEN 'Portugues'
                WHEN lang = 'Portugu??s (Brasil)' THEN 'Portugues (Brasil)'
                WHEN lang = 'Portugu??s (Portugal)' THEN 'Portugues (Portugal)'
                WHEN lang = 'Franc??s' THEN 'Frances'
                WHEN lang = 'Alem??o' THEN 'Alemao'
                WHEN lang = 'Alem??oidiomas com suporte total de ??udio' THEN 'Alemao'
                WHEN lang = 'Japon??s' THEN 'Japones'
                WHEN lang = 'Chin??s simplificado' THEN 'Chines simplificado'
                WHEN lang = 'Chin??s tradicional' THEN 'Chines tradicional'
                WHEN lang = 'Tailand??s' THEN 'Tailandes'
                WHEN lang = 'Espanhol (Am??rica Latina)' THEN 'Espanhol (America Latina)'
                WHEN lang LIKE '%fam??lia%' THEN REPLACE(lang, 'fam??lia', 'familia')
                WHEN lang LIKE '%c??mera%' THEN REPLACE(lang, 'c??mera', 'camera')
                WHEN lang LIKE '%est??reo%' THEN REPLACE(lang, 'est??reo', 'estereo')
                WHEN lang LIKE '%ajust??vel%' THEN REPLACE(lang, 'ajust??vel', 'ajustavel')
                WHEN lang LIKE '%an??lise%' THEN REPLACE(lang, 'an??lise', 'analise')
                WHEN lang LIKE '%usu??rio%' THEN REPLACE(lang, 'usu??rio', 'usuario')
                WHEN lang LIKE '%A????o%' THEN REPLACE(lang, 'A????o', 'Acao')
                WHEN lang LIKE '%Demonstra????o%' THEN REPLACE(lang, 'Demonstra????o', 'Demonstracao')
                WHEN lang LIKE '%Op????o%' THEN REPLACE(lang, 'Op????o', 'Opcao')
                WHEN lang LIKE '%Colecion??veis%' THEN REPLACE(lang, 'Colecion??veis', 'Colecionaveis')
                WHEN lang = 'idiomas com suporte total de ??udio' THEN NULL
                WHEN LOWER(lang) = 'idiomas' THEN NULL
                -- Remove qualquer ?? restante
                WHEN lang LIKE '%??%' THEN REGEXP_REPLACE(lang, '\?+', '', 'g')
                ELSE lang
            END as lang_corrigido
        FROM UNNEST(linguagens) AS lang
        WHERE CASE 
                WHEN lang = 'idiomas com suporte total de ??udio' THEN FALSE
                WHEN LOWER(lang) = 'idiomas' THEN FALSE
                ELSE TRUE
            END
    ) AS subquery
    WHERE lang_corrigido IS NOT NULL
)
WHERE linguagens::text LIKE '%??%';

-- Verifica quantos registros foram atualizados
SELECT COUNT(*) as total_registros,
       COUNT(CASE WHEN linguagens::text LIKE '%??%' THEN 1 END) as ainda_corrompidos,
       COUNT(CASE WHEN linguagens::text NOT LIKE '%??%' THEN 1 END) as corrigidos
FROM steam_bd;
