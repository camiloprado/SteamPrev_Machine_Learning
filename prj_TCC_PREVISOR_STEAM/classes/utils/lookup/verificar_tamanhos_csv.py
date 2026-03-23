"""
Script para verificar tamanhos das tabelas antes de exportar para CSV.
Útil para estimar espaço em disco necessário.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verificar_tamanhos_tabelas():
    """
    Verifica quantidade de registros e tamanho estimado em disco de cada tabela.
    """
    try:
        PostgreSQL.conectar()
        
        var_listTabelas = [
            "steam_generico",
            "steam_raw",
            "steam_generico",
            "steam_unificado",
            "itad_raw",
            "steam_itad_mapping"
        ]
        
        logger.info("=" * 80)
        logger.info("ANÁLISE DE TAMANHO DAS TABELAS (Docker PostgreSQL)")
        logger.info("=" * 80)
        
        var_dictEstatisticas = {}
        
        for var_strTabela in var_listTabelas:
            # Conta registros
            var_strSQLCount = f"SELECT COUNT(*) FROM {var_strTabela}"
            with PostgreSQL._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQLCount)
                var_intRegistros = cursor.fetchone()[0]
            
            # Tamanho da tabela em disco
            var_strSQLSize = f"""
            SELECT pg_size_pretty(pg_total_relation_size('{var_strTabela}'));
            """
            with PostgreSQL._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQLSize)
                var_strTamanho = cursor.fetchone()[0]
            
            var_dictEstatisticas[var_strTabela] = {
                "registros": var_intRegistros,
                "tamanho_disco": var_strTamanho
            }
        
        # Exibe resultados
        logger.info(f"\n{'Tabela':<25} {'Registros':>15} {'Tamanho Disco':>20}")
        logger.info("-" * 80)
        
        for var_strTabela, var_dictInfo in var_dictEstatisticas.items():
            logger.info(
                f"{var_strTabela:<25} "
                f"{var_dictInfo['registros']:>15,} "
                f"{var_dictInfo['tamanho_disco']:>20}"
            )
        
        logger.info("=" * 80)
        logger.info("ESTIMATIVA DE ESPAÇO CSV:")
        logger.info("   steam_raw: ~2-3 GB (JSONB grande)")
        logger.info("   steam_unificado: ~30-50 MB")
        logger.info("   steam_bd: ~20 MB")
        logger.info("   Demais: <20 MB cada")
        logger.info("=" * 80)
        
        return var_dictEstatisticas
        
    except Exception as e:
        logger.error(f"Erro: {e}")
        raise
    finally:
        PostgreSQL.desconectar()


if __name__ == "__main__":
    verificar_tamanhos_tabelas()