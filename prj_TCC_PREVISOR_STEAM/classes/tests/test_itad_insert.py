"""
Teste Rápido de Inserção ITAD
Testa os métodos de inserção ITAD com dados reais.
"""
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
import asyncio
import logging

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def teste_completo_itad():
    """
    Testa o fluxo completo de inserção ITAD:
    1. Busca AppIDs sem ITAD
    2. Busca dados na API ITAD
    3. Insere no PostgreSQL
    """
    try:
        logger.info("="*60)
        logger.info("TESTE: Inserção ITAD Completa")
        logger.info("="*60)
        
        # 1. Conectar ao PostgreSQL
        PostgreSQL.conectar()
        logger.info("✓ Conectado ao PostgreSQL")
        
        # 2. Buscar AppIDs sem ITAD (limitado a 10 para teste)
        logger.info("\n--- ETAPA 1: Buscar AppIDs sem ITAD ---")
        var_listTodos = PostgreSQL.buscar_appids_sem_itad(arg_intPcId=1, arg_intTotalPcs=1)
        logger.info(f"Total de AppIDs sem ITAD: {len(var_listTodos):,}")
        
        # Pega apenas 10 para teste
        var_listTeste = var_listTodos[:10]
        logger.info(f"AppIDs selecionados para teste: {var_listTeste}")
        
        # 3. Buscar dados na API ITAD
        logger.info("\n--- ETAPA 2: Buscar dados na API ITAD ---")
        var_dictDados = asyncio.run(SteamClient.lookup_itad_ids_batched(var_listTeste))
        logger.info(f"Dados obtidos do ITAD: {len(var_dictDados)}")
        
        if var_dictDados:
            logger.info("\nExemplo de dados obtidos:")
            var_intAppidExemplo = list(var_dictDados.keys())[0]
            var_dictExemplo = var_dictDados[var_intAppidExemplo]
            logger.info(f"  AppID: {var_intAppidExemplo}")
            logger.info(f"  ID ITAD: {var_dictExemplo.get('id')}")
            logger.info(f"  Slug: {var_dictExemplo.get('slug')}")
            logger.info(f"  Title: {var_dictExemplo.get('title')}")
            logger.info(f"  Type: {var_dictExemplo.get('type')}")
        
        # 4. Inserir no PostgreSQL
        logger.info("\n--- ETAPA 3: Inserir dados no PostgreSQL ---")
        var_intInseridos = PostgreSQL.inserir_dados_itad_raw_bulk(var_dictDados)
        logger.info(f"✓ Registros inseridos: {var_intInseridos}")
        
        # 5. Verificar inserção
        logger.info("\n--- ETAPA 4: Verificar dados inseridos ---")
        var_strSQL = """
        SELECT 
            sim.appid,
            sim.id_itad,
            ir.title,
            ir.ultima_atualizacao
        FROM steam_itad_mapping sim
        JOIN itad_raw ir ON sim.id_itad = ir.id_itad
        WHERE sim.appid = ANY(%s)
        ORDER BY sim.created_at DESC;
        """
        
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQL, (var_listTeste,))
            var_listResultados = cursor.fetchall()
            
            logger.info(f"Registros encontrados no banco: {len(var_listResultados)}")
            for row in var_listResultados:
                logger.info(f"  AppID {row[0]}: {row[2]} (ID: {row[1]})")
        
        # 6. Estatísticas finais
        logger.info("\n--- ESTATÍSTICAS FINAIS ---")
        var_strSQLStats = """
        SELECT 
            (SELECT COUNT(*) FROM itad_raw) as total_itad_raw,
            (SELECT COUNT(*) FROM steam_itad_mapping) as total_mapping,
            (SELECT COUNT(*) FROM steam_bd sb 
             LEFT JOIN steam_itad_mapping sim ON sb.appid = sim.appid 
             WHERE sim.appid IS NULL) as ainda_sem_itad;
        """
        
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQLStats)
            var_tupleStats = cursor.fetchone()
            logger.info(f"Total em itad_raw: {var_tupleStats[0]:,}")
            logger.info(f"Total em steam_itad_mapping: {var_tupleStats[1]:,}")
            logger.info(f"AppIDs ainda sem ITAD: {var_tupleStats[2]:,}")
        
        logger.info("\n" + "="*60)
        logger.info("✓ TESTE CONCLUÍDO COM SUCESSO!")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ Erro no teste: {e}", exc_info=True)
    finally:
        PostgreSQL.desconectar()
        logger.info("Desconectado do PostgreSQL")

def teste_busca_desatualizados():
    """
    Testa a busca de AppIDs com ITAD desatualizado.
    """
    try:
        logger.info("="*60)
        logger.info("TESTE: Buscar AppIDs ITAD Desatualizados")
        logger.info("="*60)
        
        PostgreSQL.conectar()
        
        var_listDesatualizados = PostgreSQL.buscar_appids_itad_desatualizados(
            arg_intDiasAtualizacao=90,
            arg_intPcId=1,
            arg_intTotalPcs=1
        )
        
        logger.info(f"AppIDs com ITAD >90 dias: {len(var_listDesatualizados):,}")
        if var_listDesatualizados:
            logger.info(f"Primeiros 10: {var_listDesatualizados[:10]}")
        
        logger.info("✓ Teste concluído")
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}", exc_info=True)
    finally:
        PostgreSQL.desconectar()

if __name__ == "__main__":
    logger.info("Iniciando testes ITAD...\n")
    
    # Teste 1: Inserção completa
    teste_completo_itad()
    
    # Teste 2: Busca desatualizados
    # teste_busca_desatualizados()
    
    logger.info("\n✓ Todos os testes finalizados!")
