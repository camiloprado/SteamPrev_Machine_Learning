"""
Teste do ITAD Lookup Assíncrono com Batches
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import logging
from dotenv import load_dotenv
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()


async def testar_lookup_async():
    """
    Testa o lookup ITAD assíncrono.
    """
    try:
        # Lista de AppIDs de teste (jogos populares)
        var_listAppIDs = [
            570,      # Dota 2
            730,      # Counter-Strike: Global Offensive
            440,      # Team Fortress 2
            578080,   # PUBG
            271590,   # Grand Theft Auto V
            292030,   # The Witcher 3
            1091500,  # Cyberpunk 2077
            1245620,  # Elden Ring
            1172470,  # Apex Legends
            945360,   # Among Us
        ]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTE: ITAD Lookup Assíncrono")
        logger.info(f"{'='*60}\n")
        logger.info(f"Testando com {len(var_listAppIDs)} AppIDs...")
        
        # Teste 1: Lookup simples (sem batches)
        logger.info(f"\n--- TESTE 1: Lookup simples (todos de uma vez) ---")
        var_dictResultados = await SteamClient.lookup_itad_ids(var_listAppIDs)
        
        logger.info(f"\nResultados encontrados: {len(var_dictResultados)}/{len(var_listAppIDs)}")
        
        # Exibe alguns resultados
        logger.info(f"\n{'='*60}")
        logger.info(f"AMOSTRA DE RESULTADOS:")
        logger.info(f"{'='*60}\n")
        
        for idx, (var_intAppID, var_dictDados) in enumerate(list(var_dictResultados.items())[:5]):
            logger.info(f"\nAppID {var_intAppID}:")
            logger.info(f"  ID ITAD: {var_dictDados.get('id')}")
            logger.info(f"  Title: {var_dictDados.get('title')}")
            logger.info(f"  Type: {var_dictDados.get('type')}")
        
        # Teste 2: Lookup com batches (simulando grande volume)
        logger.info(f"\n\n--- TESTE 2: Lookup com batches ---")
        
        # Cria uma lista maior duplicando os IDs
        var_listAppIDsGrande = var_listAppIDs * 5  # 50 itens
        
        logger.info(f"Testando com {len(var_listAppIDsGrande)} AppIDs em batches...")
        
        # Configura batch pequeno para teste
        Settings._var_intBatchesSize = 10
        Settings._var_intDelayBetweenBatches = 2  # Delay curto para teste
        Settings._var_intAsyncConcurrency = 3
        
        var_dictResultadosBatch = await SteamClient.lookup_itad_ids_batched(var_listAppIDsGrande)
        
        logger.info(f"\nResultados encontrados: {len(var_dictResultadosBatch)}/{len(set(var_listAppIDsGrande))}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTE CONCLUÍDO COM SUCESSO!")
        logger.info(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Erro durante o teste: {e}")
        raise


async def testar_lookup_com_dados_reais():
    """
    Testa com dados reais do banco Supabase.
    """
    try:
        from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB
        
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTE: ITAD Lookup com Dados Reais do Supabase")
        logger.info(f"{'='*60}\n")
        
        # Conecta ao Supabase
        SupabaseDB.conectar()
        
        # Busca alguns jogos
        logger.info("Buscando jogos do Supabase...")
        var_listJogos = SupabaseDB.buscar_todos_dadosSteamRaw(arg_intLimit=50)
        
        # Extrai AppIDs
        var_listAppIDs = [jogo["appid"] for jogo in var_listJogos if jogo.get("appid")]
        
        logger.info(f"Encontrados {len(var_listAppIDs)} AppIDs para lookup")
        
        # Configura batches
        Settings._var_intBatchesSize = 20
        Settings._var_intDelayBetweenBatches = 5
        Settings._var_intAsyncConcurrency = 3
        
        # Executa lookup
        var_dictResultados = await SteamClient.lookup_itad_ids_batched(var_listAppIDs)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"ESTATÍSTICAS:")
        logger.info(f"{'='*60}")
        logger.info(f"Total consultado: {len(var_listAppIDs)}")
        logger.info(f"Encontrados no ITAD: {len(var_dictResultados)}")
        logger.info(f"Não encontrados: {len(var_listAppIDs) - len(var_dictResultados)}")
        logger.info(f"Taxa de sucesso: {len(var_dictResultados)/len(var_listAppIDs):.1%}")
        
        # Desconecta
        SupabaseDB.desconectar()
        
    except Exception as e:
        logger.error(f"Erro durante o teste com dados reais: {e}")
        raise


if __name__ == "__main__":
    print("\n" + "="*60)
    print("ESCOLHA O TESTE:")
    print("="*60)
    print("1. Teste rápido com AppIDs conhecidos")
    print("2. Teste com dados reais do Supabase")
    print("="*60)
    
    var_strOpcao = input("\nEscolha (1 ou 2): ").strip()
    
    if var_strOpcao == "1":
        asyncio.run(testar_lookup_async())
    elif var_strOpcao == "2":
        asyncio.run(testar_lookup_com_dados_reais())
    else:
        print("Opção inválida!")
