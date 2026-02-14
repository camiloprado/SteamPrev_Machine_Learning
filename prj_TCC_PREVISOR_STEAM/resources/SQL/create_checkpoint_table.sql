-- Tabela para armazenar checkpoints de progresso de processamento
-- Permite retomar processamento após falhas ou interrupções

CREATE TABLE IF NOT EXISTS processing_checkpoint (
    pc_id INTEGER NOT NULL,
    tipo_processamento VARCHAR(20) NOT NULL, -- 'STEAM' ou 'ITAD'
    ultimo_indice INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pc_id, tipo_processamento)
);

-- Índice para buscas rápidas por PC e tipo
CREATE INDEX IF NOT EXISTS idx_checkpoint_pc_tipo ON processing_checkpoint(pc_id, tipo_processamento);

-- Comentários para documentação
COMMENT ON TABLE processing_checkpoint IS 'Armazena checkpoints de progresso para cada PC durante processamento';
COMMENT ON COLUMN processing_checkpoint.pc_id IS 'ID do computador processando (1, 2, 3, etc)';
COMMENT ON COLUMN processing_checkpoint.tipo_processamento IS 'Tipo de processamento: STEAM ou ITAD';
COMMENT ON COLUMN processing_checkpoint.ultimo_indice IS 'Último índice processado com sucesso';
COMMENT ON COLUMN processing_checkpoint.timestamp IS 'Data/hora do último checkpoint';
