from prj_TCC_PREVISOR_STEAM.classes.core.settings import Settings
from prj_TCC_PREVISOR_STEAM.classes.data.database import PostgreSQL

import logging

logger = logging.getLogger(__name__)

def sincronizar_generico_com_raw():
    """
    Insere AppIDs do steam_raw que estão faltando no steam_generico.
    """
    try:
        PostgreSQL.conectar()
        logger.info("Sincronizando steam_generico com steam_raw...")
        
        # Busca AppIDs que existem em steam_raw mas não em steam_generico
        var_strSQL = """
        INSERT INTO steam_generico (appid, name, ultima_atualizacao)
        SELECT 
            sr.appid,
            COALESCE(sr.detalhes->>'name', 'Desconhecido') as name,
            NOW() as ultima_atualizacao
        FROM steam_raw sr
        LEFT JOIN steam_generico sg ON sr.appid = sg.appid
        WHERE sg.appid IS NULL
          AND sr.detalhes IS NOT NULL
          AND sr.detalhes->>'name' IS NOT NULL
        ON CONFLICT (appid) DO UPDATE SET
            name = EXCLUDED.name,
            ultima_atualizacao = EXCLUDED.ultima_atualizacao
        RETURNING appid;
        """
        
        with PostgreSQL._var_connConnection.cursor() as var_curCursor:
            var_curCursor.execute(var_strSQL)
            var_listInseridos = var_curCursor.fetchall()
            var_intInseridos = len(var_listInseridos)
            PostgreSQL._var_connConnection.commit()
        
        logger.info(f"{var_intInseridos} AppIDs sincronizados de steam_raw → steam_generico")
        
        # Estatísticas finais
        var_strSQLStats = """
        SELECT 
            (SELECT COUNT(*) FROM steam_generico) as generico,
            (SELECT COUNT(*) FROM steam_raw) as raw,
            (SELECT COUNT(*) FROM steam_raw WHERE detalhes IS NOT NULL) as raw_completo,
            (SELECT COUNT(*) FROM steam_itad_mapping) as itad_mapping,
            (SELECT COUNT(*) FROM itad_raw) as itad_raw;
        """
        
        with PostgreSQL._var_connConnection.cursor() as var_curCursor:
            var_curCursor.execute(var_strSQLStats)
            stats = var_curCursor.fetchone()
        
        logger.info(f"\nESTATÍSTICAS APÓS SINCRONIZAÇÃO:")
        logger.info(f"   steam_generico: {stats[0]:,}")
        logger.info(f"   steam_raw: {stats[1]:,} (completos: {stats[2]:,})")
        logger.info(f"   steam_itad_mapping: {stats[3]:,}")
        logger.info(f"   itad_raw: {stats[4]:,}")
        
        return var_intInseridos
        
    except Exception as e:
        logger.error(f"Erro na sincronização: {e}")
        PostgreSQL._var_connConnection.rollback()
        raise
    finally:
        PostgreSQL.desconectar()

if __name__ == "__main__":
    print("=" * 60)
    print("SINCRONIZAÇÃO: steam_generico ← steam_raw")
    print("=" * 60)
    sincronizar_generico_com_raw()