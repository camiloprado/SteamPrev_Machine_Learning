"""
Script para exportar steam_unificado em formato JSON com todos os campos JSONB.
Usa batching para evitar sobrecarga de memória.
"""
import json
from prj_TCC_PREVISOR_STEAM.classes.data.database import PostgreSQL
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
    
    Parâmetros:
    - arg_strArquivoSaida: Nome do arquivo de saída
    - arg_intBatchSize: Tamanho do batch para processamento
    - arg_intLimit: Limite total de registros (None = todos)
    """
    try:
        PostgreSQL.conectar()
        
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
            
            # Processa em batches
            for offset in range(0, var_intTotal, arg_intBatchSize):
                var_intLimitBatch = min(arg_intBatchSize, var_intTotal - offset)
                
                logger.info(f"Processando registros {offset+1} a {offset+var_intLimitBatch}...")
                
                # Query com OFFSET/LIMIT
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
                ORDER BY appid
                LIMIT {var_intLimitBatch} OFFSET {offset}
                """
                
                with PostgreSQL._var_connConnection.cursor() as cursor:
                    cursor.execute(var_strSQL)
                    var_listColunas = [desc[0] for desc in cursor.description]
                    var_listResultados = cursor.fetchall()
                    
                    for var_tupleRow in var_listResultados:
                        var_dictRegistro = dict(zip(var_listColunas, var_tupleRow))
                        
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
                
                logger.info(f"✓ Batch concluído ({var_intProcessados:,}/{var_intTotal:,})")
            
            f.write('\n]')
        
        logger.info("=" * 60)
        logger.info(f"✅ Export JSON concluído!")
        logger.info(f"Arquivo: {arg_strArquivoSaida}")
        logger.info(f"Registros: {var_intProcessados:,}")
        logger.info("=" * 60)
        
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
