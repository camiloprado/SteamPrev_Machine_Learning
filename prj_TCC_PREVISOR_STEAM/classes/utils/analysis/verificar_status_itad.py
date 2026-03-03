from prj_TCC_PREVISOR_STEAM.classes.framework.InitApplication import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_generico import PostgreSQL
import logging

logger = logging.getLogger(__name__)

def verificar_status_itad():
    """
    Analisa o status atual dos dados ITAD.
    """
    try:
        PostgreSQL.conectar()
        
        logger.info("=" * 70)
        logger.info("DIAGNÓSTICO: Status dos Dados ITAD")
        logger.info("=" * 70)
        
        # 1. Total de AppIDs
        var_strSQL1 = "SELECT COUNT(*) FROM steam_generico"
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQL1)
            var_intTotalGenerico = cursor.fetchone()[0]
        
        # 2. AppIDs com ITAD válido (steam_itad_mapping)
        var_strSQL2 = "SELECT COUNT(*) FROM steam_itad_mapping"
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQL2)
            var_intComMapping = cursor.fetchone()[0]
        
        # 3. AppIDs tentados no ITAD (itad_raw)
        var_strSQL3 = "SELECT COUNT(*) FROM itad_raw"
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQL3)
            var_intTentados = cursor.fetchone()[0]
        
        # 4. AppIDs que FALHARAM no ITAD (historico_preco IS NULL)
        var_strSQL4 = "SELECT COUNT(*) FROM itad_raw WHERE historico_preco IS NULL OR slug IS NULL"
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQL4)
            var_intFalhas = cursor.fetchone()[0]
        
        # 5. AppIDs NUNCA tentados no ITAD
        var_strSQL5 = """
        SELECT COUNT(*)
        FROM steam_generico sg
        LEFT JOIN steam_itad_mapping sim ON sg.appid = sim.appid
        WHERE sim.appid IS NULL
        """
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQL5)
            var_intNuncaTentados = cursor.fetchone()[0]
        
        # Resultados
        logger.info(f"\nESTATÍSTICAS:")
        logger.info(f"   Total em steam_generico:        {var_intTotalGenerico:,}")
        logger.info(f"   Com ITAD válido (mapping):      {var_intComMapping:,} ({var_intComMapping/var_intTotalGenerico*100:.1f}%)")
        logger.info(f"   Tentados no ITAD (itad_raw):    {var_intTentados:,}")
        logger.info(f"   └─ Sucessos:                    {var_intTentados - var_intFalhas:,}")
        logger.info(f"   └─ Falhas (sem dados válidos):  {var_intFalhas:,} ⚠️")
        logger.info(f"   Nunca tentados no ITAD:         {var_intNuncaTentados:,}")
        
        var_intReprocessar = var_intFalhas + var_intNuncaTentados
        logger.info(f"\nTOTAL A REPROCESSAR:            {var_intReprocessar:,}")
        
        if var_intFalhas > 0:
            logger.info(f"\nRECOMENDAÇÃO:")
            logger.info(f"   Execute limpar_falhas_itad() para remover {var_intFalhas:,} registros falhos")
            logger.info(f"   Isso permitirá reprocessá-los no próximo run")
        
        return {
            "total": var_intTotalGenerico,
            "com_mapping": var_intComMapping,
            "tentados": var_intTentados,
            "falhas": var_intFalhas,
            "nunca_tentados": var_intNuncaTentados,
            "reprocessar": var_intReprocessar
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar status ITAD: {e}")
        raise
    finally:
        PostgreSQL.desconectar()


def limpar_falhas_itad():
    """
    Remove registros em itad_raw onde plain IS NULL para permitir reprocessamento.
    """
    try:
        PostgreSQL.conectar()
        
        logger.info("=" * 70)
        logger.info("LIMPEZA: Removendo Falhas do ITAD")
        logger.info("=" * 70)
        
        var_strSQL = "DELETE FROM itad_raw WHERE historico_preco IS NULL OR slug IS NULL RETURNING slug, id_itad"
        
        with PostgreSQL._var_connConnection.cursor() as cursor:
            cursor.execute(var_strSQL)
            var_listRemovidos = cursor.fetchall()
            PostgreSQL._var_connConnection.commit()
        
        logger.info(f"\n{len(var_listRemovidos):,} registros falhos removidos")
        logger.info(f"   Agora estes AppIDs podem ser reprocessados")
        
        return var_listRemovidos
        
    except Exception as e:
        logger.error(f"Erro ao limpar falhas ITAD: {e}")
        PostgreSQL._var_connConnection.rollback()
        raise
    finally:
        PostgreSQL.desconectar()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("VERIFICAÇÃO E LIMPEZA DE DADOS ITAD")
    print("=" * 70 + "\n")
    
    # Passo 1: Verificar status
    stats = verificar_status_itad()
    
    # Passo 2: Perguntar se quer limpar
    if stats["falhas"] > 0:
        print("\n" + "=" * 70)
        resposta = input(f"Deseja remover {stats['falhas']:,} registros falhos? (s/n): ")
        
        if resposta.lower() == 's':
            limpar_falhas_itad()
            
            print("\nPronto! Execute agora:")
            print("   python prj_TCC_PREVISOR_STEAM/classes/SQL/reprocessaITAD.py")
        else:
            print("\nLimpeza cancelada")
    else:
        print("\nNenhuma falha para limpar!")