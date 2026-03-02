from prj_TCC_PREVISOR_STEAM.classes.framework.InitApplication import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient

import sys
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

async def reprocessar_itad_faltantes():
    """
    Busca AppIDs que agora existem em steam_generico mas não têm ITAD.
    """
    try:
        PostgreSQL.conectar()
        
        # Busca AppIDs sem ITAD (agora com steam_generico atualizado)
        logger.info("Buscando AppIDs sem dados ITAD...")
        var_listAppids = PostgreSQL.buscar_appids_sem_itad()
        
        logger.info(f"Encontrados {len(var_listAppids):,} AppIDs sem ITAD")
        
        if not var_listAppids:
            logger.info("Todos os AppIDs já têm dados ITAD!")
            return
        
        # Processa em lotes
        var_intRange = int(os.getenv("RANGE_PROCESSAMENTO_ITAD_RAW", 1000))
        var_intTotal = len(var_listAppids)
        var_intSucesso = 0
        
        for i in range(0, var_intTotal, var_intRange):
            var_listLote = var_listAppids[i:i+var_intRange]
            var_intLote = i // var_intRange + 1
            var_intTotalLotes = (var_intTotal + var_intRange - 1) // var_intRange
            
            logger.info(f"Processando lote {var_intLote}/{var_intTotalLotes} ({len(var_listLote)} AppIDs)...")
            
            # Busca dados ITAD
            var_dictDados = await SteamClient.lookup_itad_ids_batched(arg_seqAppids=var_listLote)
            
            # Insere no banco
            if var_dictDados:
                var_intInseridos = PostgreSQL.inserir_dados_itad_raw_bulk(var_dictDados)
                var_intSucesso += var_intInseridos
                logger.info(f"{var_intInseridos} registros inseridos no ITAD (Total: {var_intSucesso})")
            
            # Pausa entre lotes
            await asyncio.sleep(2)
        
        logger.info(f"\nReprocessamento ITAD concluído! Total inserido: {var_intSucesso}")
        
    except Exception as e:
        logger.error(f"Erro no reprocessamento ITAD: {e}")
        raise
    finally:
        PostgreSQL.desconectar()

if __name__ == "__main__":
    print("=" * 60)
    print("REPROCESSAMENTO: Dados ITAD Faltantes")
    print("=" * 60)
    asyncio.run(reprocessar_itad_faltantes())