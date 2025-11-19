-- Script completo para limpar e normalizar linguagens no steam_bd

UPDATE steam_bd
SET linguagens = (
    SELECT ARRAY_AGG(lang_final ORDER BY ord)
    FROM (
        SELECT DISTINCT ON (lang_final) 
            lang_final,
            ROW_NUMBER() OVER () as ord
        FROM (
            SELECT 
                CASE 
                    -- Correções de caracteres corrompidos específicos
                    WHEN lang_limpo = 'Ingls' OR lang_limpo LIKE 'Ingl%s' THEN 'Ingles'
                    WHEN lang_limpo = 'Portugu??s' OR lang_limpo LIKE 'Portugu%s' THEN 'Portugues'
                    WHEN lang_limpo = 'Portugu??s (Brasil)' OR lang_limpo LIKE 'Portugu%s (Brasil)' THEN 'Portugues (Brasil)'
                    WHEN lang_limpo = 'Portugu??s (Portugal)' OR lang_limpo LIKE 'Portugu%s (Portugal)' THEN 'Portugues (Portugal)'
                    WHEN lang_limpo = 'Francs' OR lang_limpo LIKE 'Franc%s' THEN 'Frances'
                    WHEN lang_limpo = 'Alemo' OR lang_limpo LIKE 'Alem%o' THEN 'Alemao'
                    WHEN lang_limpo = 'Japon??s' OR lang_limpo LIKE 'Japon%s' THEN 'Japones'
                    WHEN lang_limpo LIKE 'Chin%s simplificado' THEN 'Chines simplificado'
                    WHEN lang_limpo LIKE 'Chin%s tradicional' THEN 'Chines tradicional'
                    WHEN lang_limpo = 'Tailand??s' OR lang_limpo LIKE 'Tailand%s' THEN 'Tailandes'
                    WHEN lang_limpo LIKE 'Espanhol (Am%rica Latina)' THEN 'Espanhol (America Latina)'
                    WHEN lang_limpo = 'Espanhol (Espanha)' THEN 'Espanhol (Espanha)'
                    WHEN lang_limpo = 'Italiano' THEN 'Italiano'
                    WHEN lang_limpo = 'Russo' THEN 'Russo'
                    WHEN lang_limpo = 'Coreano' THEN 'Coreano'
                    WHEN lang_limpo = 'Ingles' THEN 'Ingles'
                    -- Substituições de frases
                    WHEN lang_limpo LIKE '%fam%lia%' THEN REGEXP_REPLACE(lang_limpo, 'fam[^a]*lia', 'familia', 'g')
                    WHEN lang_limpo LIKE '%c%mera%' THEN REGEXP_REPLACE(lang_limpo, 'c[^a]*mera', 'camera', 'g')
                    WHEN lang_limpo LIKE '%est%reo%' THEN REGEXP_REPLACE(lang_limpo, 'est[^e]*reo', 'estereo', 'g')
                    WHEN lang_limpo LIKE '%ajust%vel%' THEN REGEXP_REPLACE(lang_limpo, 'ajust[^a]*vel', 'ajustavel', 'g')
                    WHEN lang_limpo LIKE '%an%lise%' THEN REGEXP_REPLACE(lang_limpo, 'an[^a]*lise', 'analise', 'g')
                    WHEN lang_limpo LIKE '%usu%rio%' THEN REGEXP_REPLACE(lang_limpo, 'usu[^a]*rio', 'usuario', 'g')
                    WHEN lang_limpo LIKE '%A%o' THEN REGEXP_REPLACE(lang_limpo, 'A[^c]*o', 'Acao', 'g')
                    WHEN lang_limpo LIKE '%Demonstra%o%' THEN REGEXP_REPLACE(lang_limpo, 'Demonstra[^c]*o', 'Demonstracao', 'g')
                    WHEN lang_limpo LIKE '%Op%o%' THEN REGEXP_REPLACE(lang_limpo, 'Op[^c]*o', 'Opcao', 'g')
                    WHEN lang_limpo LIKE '%Colecion%veis%' THEN REGEXP_REPLACE(lang_limpo, 'Colecion[^a]*veis', 'Colecionaveis', 'g')
                    -- Remove ?? restantes
                    WHEN lang_limpo LIKE '%?%' THEN REGEXP_REPLACE(lang_limpo, '\?+', '', 'g')
                    ELSE lang_limpo
                END as lang_final
            FROM (
                SELECT 
                    -- Remove tags HTML, quebras de linha, pontuação estranha
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(
                            REGEXP_REPLACE(
                                TRIM(lang),
                                E'[\\r\\n\\t]+', '', 'g'  -- Remove quebras de linha
                            ),
                            '<[^>]+>|\[/?[bi]\]|\*', '', 'g'  -- Remove tags HTML e markdown
                        ),
                        '[;,]+$', '', 'g'  -- Remove pontuação no final
                    ) as lang_limpo
                FROM UNNEST(linguagens) AS lang
            ) AS cleaned
            WHERE lang_limpo IS NOT NULL 
              AND LENGTH(TRIM(lang_limpo)) > 2
              AND LOWER(lang_limpo) NOT IN ('idiomas', 'idiomas com suporte total de audio', 'idiomas com suporte total de udio')
        ) AS normalized
        WHERE lang_final IS NOT NULL AND LENGTH(TRIM(lang_final)) > 2
    ) AS final
)
WHERE EXISTS (
    SELECT 1 
    FROM UNNEST(linguagens) AS lang
    WHERE lang LIKE '%[%' 
       OR lang LIKE '%]%' 
       OR lang LIKE '%??%'
       OR lang LIKE '%\r%'
       OR lang LIKE '%\n%'
       OR lang LIKE '%;%'
       OR lang LIKE '%*%'
       OR lang ~ '[^[:print:]]'
);

-- Relatório de correção
SELECT 
    COUNT(*) as total_registros,
    COUNT(CASE WHEN linguagens::text LIKE '%[%' OR linguagens::text LIKE '%??%' THEN 1 END) as ainda_com_problemas,
    COUNT(CASE WHEN linguagens::text NOT LIKE '%[%' AND linguagens::text NOT LIKE '%??%' THEN 1 END) as limpos
FROM steam_bd;
