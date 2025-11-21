-- Cria tabela de mapeamento entre Steam AppID e ITAD ID
-- Necessário porque a API ITAD retorna id_itad, não appid

CREATE TABLE IF NOT EXISTS steam_itad_mapping (
    appid INTEGER PRIMARY KEY,
    id_itad VARCHAR NOT NULL,
    slug VARCHAR,
    title VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (appid) REFERENCES steam_generico(appid) ON DELETE CASCADE,
    FOREIGN KEY (id_itad) REFERENCES itad_raw(id_itad) ON DELETE CASCADE
);

-- Índices para otimizar buscas
CREATE INDEX IF NOT EXISTS idx_steam_itad_mapping_id_itad ON steam_itad_mapping(id_itad);
CREATE INDEX IF NOT EXISTS idx_steam_itad_mapping_appid ON steam_itad_mapping(appid);

-- Comentários
COMMENT ON TABLE steam_itad_mapping IS 'Mapeia Steam AppIDs para ITAD IDs retornados pela API lookup';
COMMENT ON COLUMN steam_itad_mapping.appid IS 'Steam Application ID';
COMMENT ON COLUMN steam_itad_mapping.id_itad IS 'ITAD ID retornado pela API';
COMMENT ON COLUMN steam_itad_mapping.slug IS 'Slug ITAD do jogo';
COMMENT ON COLUMN steam_itad_mapping.title IS 'Título do jogo no ITAD';

-- Verifica a criação
SELECT 
    table_name, 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE table_name = 'steam_itad_mapping' 
ORDER BY ordinal_position;
