"""
Script para sincronizar steam_unificado do Docker PostgreSQL para Supabase.
Executa migração em batches com controle de progresso.
"""
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def sincronizar_steam_unificado(arg_intBatchSize: int = 500, arg_intLimit: int = None):
    """
    Sincroniza dados de steam_unificado do Docker para Supabase.
    
    Parâmetros:
    - arg_intBatchSize (int): Tamanho do batch (padrão: 500)
    - arg_intLimit (int): Limite total de registros (None = todos)
    """
    try:
        # Conecta aos bancos
        logger.info("Conectando ao Docker PostgreSQL...")
        PostgreSQL.conectar()
        
        logger.info("Conectando ao Supabase...")
        SupabaseDB.conectar()
        
        # Verifica totais
        logger.info("Verificando totais...")
        var_listTodosDados = PostgreSQL.buscar_todos_steam_unificado(arg_intLimit)
        var_intTotalDocker = len(var_listTodosDados)
        var_intTotalSupabase = SupabaseDB.contar_steam_unificado()
        
        logger.info(f"Docker: {var_intTotalDocker:,} registros")
        logger.info(f"Supabase: {var_intTotalSupabase:,} registros")
        
        if var_intTotalDocker == 0:
            logger.warning("Nenhum registro encontrado no Docker!")
            return
        
        # Processa em batches
        var_intTotalInseridos = 0
        var_intTotalErros = 0
        
        for i in range(0, var_intTotalDocker, arg_intBatchSize):
            var_intFim = min(i + arg_intBatchSize, var_intTotalDocker)
            var_listBatch = var_listTodosDados[i:var_intFim]
            
            logger.info(f"Processando registros {i+1} a {var_intFim} de {var_intTotalDocker:,}...")
            
            try:
                SupabaseDB.inserir_steam_unificado_bulk(var_listBatch)
                var_intTotalInseridos += len(var_listBatch)
                logger.info(f"✓ Batch inserido com sucesso ({var_intTotalInseridos:,}/{var_intTotalDocker:,})")
            except Exception as e:
                logger.error(f"✗ Erro no batch {i+1}-{var_intFim}: {e}")
                var_intTotalErros += len(var_listBatch)
        
        # Verifica resultado final
        var_intTotalSupabaseFinal = SupabaseDB.contar_steam_unificado()
        
        logger.info("=" * 60)
        logger.info("SINCRONIZAÇÃO CONCLUÍDA")
        logger.info("=" * 60)
        logger.info(f"Registros no Docker: {var_intTotalDocker:,}")
        logger.info(f"Inseridos com sucesso: {var_intTotalInseridos:,}")
        logger.info(f"Erros: {var_intTotalErros:,}")
        logger.info(f"Total final no Supabase: {var_intTotalSupabaseFinal:,}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Erro fatal na sincronização: {e}")
        raise

if __name__ == "__main__":
    import sys
    
    # Argumentos opcionais via linha de comando
    var_intBatchSize = 500
    var_intLimit = None
    
    if len(sys.argv) > 1:
        try:
            var_intBatchSize = int(sys.argv[1])
        except:
            logger.warning(f"Batch size inválido, usando padrão: {var_intBatchSize}")
    
    if len(sys.argv) > 2:
        try:
            var_intLimit = int(sys.argv[2])
            logger.info(f"Limitando a {var_intLimit:,} registros (modo teste)")
        except:
            pass
    
    logger.info("Iniciando sincronização steam_unificado...")
    logger.info(f"Batch size: {var_intBatchSize}")
    
    sincronizar_steam_unificado(var_intBatchSize, var_intLimit)
