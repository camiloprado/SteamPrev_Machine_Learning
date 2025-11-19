-- Aumenta o limite da coluna 'nome' de VARCHAR(255) para VARCHAR(600)
-- Isso acomoda jogos com nomes muito longos (máximo encontrado: 542 caracteres)

ALTER TABLE steam_bd 
ALTER COLUMN nome TYPE VARCHAR(600);

-- Verifica a alteração
SELECT 
    column_name, 
    data_type, 
    character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'steam_bd' 
  AND column_name = 'nome';
