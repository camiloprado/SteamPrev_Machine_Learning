-- ============================================
-- CRIAÇÃO DA TABELA STEAM_UNIFICADO NO SUPABASE
-- ============================================
-- Execute este SQL no Supabase Dashboard > SQL Editor
-- ou via API REST

-- Criar tabela steam_unificado
CREATE TABLE IF NOT EXISTS steam_unificado (
    appid INTEGER PRIMARY KEY,
    nome VARCHAR(600) NOT NULL,
    
    -- Dados estruturados
    classificacao_etaria VARCHAR(50),
    linguagens TEXT[],
    desenvolvedores TEXT[],
    distribuidores TEXT[],
    preco VARCHAR(50),
    metacritic_score VARCHAR(20),
    categorias TEXT[],
    genero TEXT[],
    data_lancamento VARCHAR(50),
    type VARCHAR(50),
    
    -- Reviews estruturados
    review_score INTEGER,
    total_reviews INTEGER,
    total_negative INTEGER,
    total_positive INTEGER,
    review_score_desc VARCHAR(255),
    
    -- JSONB para dados completos/flexíveis
    detalhes_completos JSONB,
    reviews_completos JSONB,
    
    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar índices para otimização
CREATE INDEX IF NOT EXISTS idx_steam_unificado_nome ON steam_unificado(nome);
CREATE INDEX IF NOT EXISTS idx_steam_unificado_type ON steam_unificado(type);
CREATE INDEX IF NOT EXISTS idx_steam_unificado_data_lancamento ON steam_unificado(data_lancamento);
CREATE INDEX IF NOT EXISTS idx_steam_unificado_atualizacao ON steam_unificado(ultima_atualizacao);
CREATE INDEX IF NOT EXISTS idx_steam_unificado_reviews ON steam_unificado(total_reviews DESC);
CREATE INDEX IF NOT EXISTS idx_steam_unificado_preco ON steam_unificado(preco);

-- Comentários da tabela
COMMENT ON TABLE steam_unificado IS 'Tabela unificada consolidando steam_raw + steam_bd + steam_generico';
COMMENT ON COLUMN steam_unificado.detalhes_completos IS 'Dados completos da API Steam em formato JSONB';
COMMENT ON COLUMN steam_unificado.reviews_completos IS 'Reviews completos da API Steam em formato JSONB';

-- Habilitar Row Level Security (RLS) - IMPORTANTE para Supabase
ALTER TABLE steam_unificado ENABLE ROW LEVEL SECURITY;

-- Criar política de acesso público para leitura (ajuste conforme necessidade)
CREATE POLICY "Enable read access for all users" ON steam_unificado
    FOR SELECT
    USING (true);

-- Criar política de acesso para service_role (sua API/backend)
CREATE POLICY "Enable full access for service role" ON steam_unificado
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================
-- SCRIPT COMPLETO - PRONTO PARA EXECUTAR
-- ============================================
