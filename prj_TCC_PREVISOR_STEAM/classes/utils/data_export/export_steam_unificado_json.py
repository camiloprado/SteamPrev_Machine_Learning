"""
Script para exportar steam_unificado em formato JSON com todos os campos JSONB.
Usa batching para evitar sobrecarga de memória.
"""
import json
import time
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def exportar_steam_unificado_json(
    arg_strArquivoSaida: str = "steam_unificado_complete.json",
    arg_intBatchSize: int = 1000,
    arg_intLimit: int = None
):
    """
    Exporta steam_unificado para JSON incluindo todos os campos JSONB.
    Usa KEYSET PAGINATION (cursor-based) para manter performance constante.
    
    Parâmetros:
    - arg_strArquivoSaida: Nome do arquivo de saída
    - arg_intBatchSize: Tamanho do batch para processamento
    - arg_intLimit: Limite total de registros (None = todos)
    """
    try:
        PostgreSQL.conectar()
        
        # ========== VERIFICAÇÃO DE ÍNDICE ==========
        logger.info("Verificando índices na tabela steam_unificado...")
        var_strSQLIndices = """
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = 'steam_unificado' AND indexdef LIKE '%appid%';
        """
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQLIndices)
            var_listIndices = cursor.fetchall()
            if var_listIndices:
                logger.info(f"✓ Índice encontrado em appid: {var_listIndices[0][0]}")
            else:
                logger.warning(
                    "⚠️  ATENÇÃO: Nenhum índice encontrado em 'appid'!\n"
                    "   Performance será MUITO LENTA sem índice.\n"
                    "   Recomendação: CREATE INDEX idx_steam_unificado_appid ON steam_unificado(appid);"
                )
        # ==========================================
        
        # Query para contar total
        logger.info("Contando registros...")
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM steam_unificado")
            var_intTotal = cursor.fetchone()[0]
        
        if arg_intLimit:
            var_intTotal = min(var_intTotal, arg_intLimit)
        
        logger.info(f"Total de registros a exportar: {var_intTotal:,}")
        
        # Abre arquivo para escrita
        with open(arg_strArquivoSaida, 'w', encoding='utf-8') as f:
            f.write('[\n')
            
            var_intProcessados = 0
            var_boolPrimeiro = True
            var_intUltimoAppid = 0  # Cursor para keyset pagination
            
            # ========== BATCH SIZE ADAPTATIVO ==========
            var_intBatchSizeAtual = arg_intBatchSize
            var_intBatchSizeMin = 100  # Mínimo seguro
            var_intBatchSizeMax = arg_intBatchSize  # Máximo inicial
            var_floatTempoLimite = 10.0  # Se batch demora >10s, reduz tamanho
            var_listTemposBatch = []  # Histórico para análise
            # ==========================================
            
            # Processa em batches usando KEYSET PAGINATION (muito mais rápido!)
            while var_intProcessados < var_intTotal:
                var_intLimitBatch = min(var_intBatchSizeAtual, var_intTotal - var_intProcessados)
                
                logger.info(f"Processando registros {var_intProcessados+1} a {var_intProcessados+var_intLimitBatch}... (batch size: {var_intBatchSizeAtual})")
                var_floatInicioBatch = time.time()
                
                # Query com KEYSET PAGINATION (WHERE appid > last) - performance constante!
                var_strSQL = f"""
                SELECT 
                    appid, nome, classificacao_etaria, linguagens, desenvolvedores,
                    distribuidores, preco, metacritic_score, categorias, genero,
                    data_lancamento, type, review_score, total_reviews, total_negative,
                    total_positive, review_score_desc, 
                    detalhes_completos::text as detalhes_completos,
                    reviews_completos::text as reviews_completos,
                    ultima_atualizacao
                FROM steam_unificado
                WHERE appid > {var_intUltimoAppid}
                ORDER BY appid
                LIMIT {var_intLimitBatch}
                """
                
                with PostgreSQL._var_connConnection.cursor() as cursor:
                    cursor.execute(var_strSQL)
                    var_listColunas = [desc[0] for desc in cursor.description]
                    var_listResultados = cursor.fetchall()
                    
                    if not var_listResultados:
                        logger.warning(f"Nenhum resultado após appid {var_intUltimoAppid}. Finalizando.")
                        break
                    
                    for var_tupleRow in var_listResultados:
                        var_dictRegistro = dict(zip(var_listColunas, var_tupleRow))
                        
                        # Atualiza cursor para próximo batch
                        var_intUltimoAppid = var_dictRegistro['appid']
                        
                        # Converte timestamp para string
                        if var_dictRegistro.get('ultima_atualizacao'):
                            var_dictRegistro['ultima_atualizacao'] = var_dictRegistro['ultima_atualizacao'].isoformat()
                        
                        # Parse JSONB de volta para dict
                        if var_dictRegistro.get('detalhes_completos'):
                            try:
                                var_dictRegistro['detalhes_completos'] = json.loads(var_dictRegistro['detalhes_completos'])
                            except:
                                pass
                        
                        if var_dictRegistro.get('reviews_completos'):
                            try:
                                var_dictRegistro['reviews_completos'] = json.loads(var_dictRegistro['reviews_completos'])
                            except:
                                pass
                        
                        # Escreve no arquivo
                        if not var_boolPrimeiro:
                            f.write(',\n')
                        else:
                            var_boolPrimeiro = False
                        
                        json.dump(var_dictRegistro, f, ensure_ascii=False, indent=2)
                        var_intProcessados += 1
                
                # ========== ANÁLISE DE PERFORMANCE E AJUSTE ==========
                var_floatTempoBatch = time.time() - var_floatInicioBatch
                var_listTemposBatch.append(var_floatTempoBatch)
                var_floatTempoPorRegistro = var_floatTempoBatch / len(var_listResultados) if var_listResultados else 0
                
                # Log detalhado de performance
                logger.info(
                    f"✓ Batch concluído ({var_intProcessados:,}/{var_intTotal:,}) | "
                    f"Tempo: {var_floatTempoBatch:.1f}s | "
                    f"Registros/s: {len(var_listResultados)/var_floatTempoBatch:.1f}"
                )
                
                # ========== BATCH SIZE ADAPTATIVO ==========
                # Se batch está muito lento (>10s), REDUZ o tamanho
                if var_floatTempoBatch > var_floatTempoLimite and var_intBatchSizeAtual > var_intBatchSizeMin:
                    var_intBatchSizeAntigo = var_intBatchSizeAtual
                    var_intBatchSizeAtual = max(var_intBatchSizeMin, var_intBatchSizeAtual // 2)
                    logger.warning(
                        f"⚠️  Performance degradando! Reduzindo batch: {var_intBatchSizeAntigo} → {var_intBatchSizeAtual} "
                        f"(último batch: {var_floatTempoBatch:.1f}s)"
                    )
                
                # Se batch está rápido (<5s) e há margem, AUMENTA o tamanho
                elif var_floatTempoBatch < 5.0 and var_intBatchSizeAtual < var_intBatchSizeMax:
                    var_intBatchSizeAtual = min(var_intBatchSizeMax, int(var_intBatchSizeAtual * 1.5))
                    logger.info(f"✓ Performance boa! Aumentando batch para {var_intBatchSizeAtual}")
                # ==============================================
            
            f.write('\n]')
        
        # ========== ESTATÍSTICAS FINAIS ==========
        var_floatTempoTotal = sum(var_listTemposBatch)
        var_floatTempoMedio = var_floatTempoTotal / len(var_listTemposBatch) if var_listTemposBatch else 0
        var_floatTempoMin = min(var_listTemposBatch) if var_listTemposBatch else 0
        var_floatTempoMax = max(var_listTemposBatch) if var_listTemposBatch else 0
        
        logger.info("=" * 70)
        logger.info(f"✅ Export JSON concluído!")
        logger.info(f"Arquivo: {arg_strArquivoSaida}")
        logger.info(f"Registros: {var_intProcessados:,}")
        logger.info(f"")
        logger.info(f"📊 Performance:")
        logger.info(f"   Total de batches: {len(var_listTemposBatch)}")
        logger.info(f"   Tempo total: {var_floatTempoTotal/60:.1f} minutos")
        logger.info(f"   Tempo por batch: {var_floatTempoMedio:.1f}s (média) | {var_floatTempoMin:.1f}s (min) | {var_floatTempoMax:.1f}s (max)")
        logger.info(f"   Registros/segundo: {var_intProcessados/var_floatTempoTotal:.1f} (média geral)")
        if var_floatTempoMax > var_floatTempoMin * 3:
            logger.warning(
                f"   ⚠️  Degradação detectada: batch mais lento foi {var_floatTempoMax/var_floatTempoMin:.1f}x mais lento que o mais rápido!\n"
                f"   Recomendação: Crie índice em appid: CREATE INDEX idx_steam_unificado_appid ON steam_unificado(appid);"
            )
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Erro durante export: {e}")
        raise

if __name__ == "__main__":
    import sys
    
    # Argumentos: [arquivo_saida] [batch_size] [limit]
    arquivo = sys.argv[1] if len(sys.argv) > 1 else "prj_TCC_PREVISOR_STEAM/resources/dados/steam_unificado_complete.json"
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    if limit:
        logger.info(f"MODO TESTE: Limitando a {limit:,} registros")
        arquivo = arquivo.replace('.json', f'_sample_{limit}.json')
    
    exportar_steam_unificado_json(arquivo, batch_size, limit)
