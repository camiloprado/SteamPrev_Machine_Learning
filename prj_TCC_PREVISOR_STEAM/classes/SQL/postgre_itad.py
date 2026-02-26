from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL

from datetime import datetime
from psycopg2.extras import execute_batch, execute_values
from psycopg2 import pool
from time import sleep
from typing import Generator
import psycopg2, json, logging

logger = logging.getLogger(__name__)

class PostgreSQLITAD(PostgreSQL):
    """
    Classe para operações com PostgreSQL.
    """

    @classmethod
    def buscar_appids_sem_itad(cls, arg_intLimit: int = None) -> list:
        """
        Busca AppIDs que NÃO têm dados ITAD válidos (steam_itad_mapping).
        
        Retorna AppIDs que NÃO estão em steam_itad_mapping (nunca processados ou falharam).
        
        Args:
            arg_intLimit: Limite de resultados (None = todos)
        
        Returns:
            Lista de AppIDs sem dados ITAD válidos
        """
        var_connConnection = cls.conectar()
        
        try:
            var_strSQL = """
            SELECT sg.appid
            FROM steam_generico sg
            LEFT JOIN steam_itad_mapping sim ON sg.appid = sim.appid
            WHERE sim.appid IS NULL
            ORDER BY sg.appid
            """
            
            if arg_intLimit:
                var_strSQL += f" LIMIT {arg_intLimit}"
            
            with var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL)
                var_listResultados = [row[0] for row in cursor.fetchall()]
            
            return var_listResultados
            
        except Exception as e:
            raise Exception(f"Erro ao buscar AppIDs sem ITAD: {e}")
        
        finally:
            cls.desconectar(var_connConnection)
    
    @classmethod
    def buscar_appids_itad_desatualizados(cls, arg_intDiasAtualizacao: int = None, arg_intPcId: int = 1, arg_intTotalPcs: int = 1) -> list[int]:
        """
        Busca AppIDs com dados ITAD desatualizados na tabela itad_raw.
        
        Parâmetros:
        - arg_intDiasAtualizacao (int): Dias para considerar desatualizado. (Padrão: 90)
        - arg_intPcId (int): ID deste PC. (Padrão: 1)
        - arg_intTotalPcs (int): Total de PCs. (Padrão: 1)
        
        Retorna:
        - list[int]: Lista de AppIDs com ITAD desatualizado
        """
        var_connConnection = cls.conectar()
        try:
            var_intDias = arg_intDiasAtualizacao or 90  # ITAD atualiza menos frequentemente
            var_dataCorte = datetime.now() - __import__('datetime').timedelta(days=var_intDias)
            
            logger.info(f"Buscando AppIDs ITAD desatualizados (>{var_intDias} dias)...")
            
            var_strSQL = """
            SELECT sim.appid 
            FROM steam_itad_mapping sim
            JOIN itad_raw ir ON sim.id_itad = ir.id_itad
            WHERE ir.ultima_atualizacao < %s
            """
            
            # Aplica filtro de PC se necessário
            if arg_intTotalPcs > 1:
                var_strSQL += f" AND MOD(sim.appid, {arg_intTotalPcs}) = {arg_intPcId - 1}"
            
            var_strSQL += ";"
            
            with var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, (var_dataCorte,))
                var_listResultados = cursor.fetchall()
                var_listAppids = [row[0] for row in var_listResultados]
                
                logger.info(f"Encontrados {len(var_listAppids):,} AppIDs ITAD desatualizados")
                return var_listAppids
                
        except Exception as e:
            raise Exception(f"Erro ao buscar AppIDs ITAD desatualizados: {e}")

        finally:
            cls.desconectar(var_connConnection)

    @classmethod
    def inserir_dados_itad_raw_bulk(cls, arg_dictDadosItad: dict[int, dict]) -> int:
        """
        Insere ou atualiza dados na tabela itad_raw e steam_itad_mapping em bulk.
        
        Parâmetros:
        - arg_dictDadosItad (dict): Dicionário mapeando appid -> dados ITAD
                                    Estrutura esperada: {appid: {"id": str, "slug": str, "title": str, ...}}
        
        Retorna:
        - int: Número de registros inseridos/atualizados
        """
        var_connConnection = cls.conectar()
        try:
            if not arg_dictDadosItad:
                logger.warning("Nenhum dado ITAD fornecido para inserção")
                return 0
            
            var_intInseridos = 0
            var_dateNow = datetime.now()
            
            for var_intAppid, var_dictDados in arg_dictDadosItad.items():
                try:
                    if var_dictDados == "AUSENTE":
                        # Extrai dados do ITAD
                        var_strIdItad = "AUSENTE"
                        var_strSlug = "AUSENTE"
                        var_strTitle = "AUSENTE"
                        var_strType = "AUSENTE"
                        var_boolMature = False
                        var_jsonAssets = json.dumps({})
                    else:
                        # Extrai dados do ITAD
                        var_strIdItad = var_dictDados.get("id")
                        var_strSlug = var_dictDados.get("slug")
                        var_strTitle = var_dictDados.get("title")
                        var_strType = var_dictDados.get("type")
                        var_boolMature = var_dictDados.get("mature", False)
                        var_jsonAssets = json.dumps(var_dictDados.get("assets", {}))
                    
                    if not var_strIdItad:
                        logger.warning(f"AppID {var_intAppid}: ID ITAD ausente, pulando")
                        continue
                    
                    with var_connConnection.cursor() as cursor:
                        # 1. Insere/atualiza na tabela itad_raw
                        var_strSQLItadRaw = """
                        INSERT INTO itad_raw (id_itad, slug, title, type, mature, assets, ultima_atualizacao)
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                        ON CONFLICT (id_itad) 
                        DO UPDATE SET
                            slug = EXCLUDED.slug,
                            title = EXCLUDED.title,
                            type = EXCLUDED.type,
                            mature = EXCLUDED.mature,
                            assets = EXCLUDED.assets,
                            ultima_atualizacao = EXCLUDED.ultima_atualizacao;
                        """
                        cursor.execute(var_strSQLItadRaw, (
                            var_strIdItad, var_strSlug, var_strTitle, 
                            var_strType, var_boolMature, var_jsonAssets, var_dateNow
                        ))
                        
                        # 2. Insere/atualiza na tabela steam_itad_mapping
                        var_strSQLMapping = """
                        INSERT INTO steam_itad_mapping (appid, id_itad, slug, title)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (appid)
                        DO UPDATE SET
                            id_itad = EXCLUDED.id_itad,
                            slug = EXCLUDED.slug,
                            title = EXCLUDED.title;
                        """
                        cursor.execute(var_strSQLMapping, (
                            var_intAppid, var_strIdItad, var_strSlug, var_strTitle
                        ))
                        
                        # Commit individual para cada registro
                        var_connConnection.commit()
                        var_intInseridos += 1
                        
                except Exception as e:
                    # Rollback em caso de erro
                    var_connConnection.rollback()
                    logger.error(f"Erro ao inserir AppID {var_intAppid} no ITAD: {e}")
                    continue
            
            logger.info(f"Inseridos/atualizados {var_intInseridos:,} registros no ITAD (itad_raw + steam_itad_mapping)")
            return var_intInseridos
                
        except Exception as e:
            logger.error(f"Erro geral ao inserir dados ITAD em bulk: {e}\")")
            return var_intInseridos

        finally:
            cls.desconectar(var_connConnection)

    @classmethod
    def inserir_dados_itad_raw_historico_preco_bulk(cls, arg_dictDadosItad: dict[str, list[dict]]) -> int:
        """
        Insere dados históricos de preços na tabela itad_raw em bulk.
        
        Parâmetros:
        - arg_dictDadosItad (dict): Dicionário mapeando ID_ITAD -> lista de registros históricos
        
        Retorna:
        - int: Número de registros inseridos
        """
        var_connConnection = cls.conectar()
        try:
            if not arg_dictDadosItad:
                logger.warning("Nenhum dado histórico de preços fornecido para inserção")
                return 0
            
            var_intInseridos = 0
            var_dateNow = datetime.now()

            for var_strIDITAD, var_listHistorico in arg_dictDadosItad.items():
                try:
                    with var_connConnection.cursor() as cursor:
                        var_strSQLHistorico = """
                        UPDATE itad_raw
                        SET historico_preco = %s::jsonb,
                            ultima_atualizacao = %s
                        WHERE id_itad = %s;
                        """
                        
                        # Converte lista para JSON string
                        var_strHistoricoJson = json.dumps(var_listHistorico) if var_listHistorico else None
                        
                        cursor.execute(var_strSQLHistorico, (var_strHistoricoJson, var_dateNow, var_strIDITAD))
                        
                        # Verifica se algum registro foi atualizado
                        if cursor.rowcount > 0:
                            var_connConnection.commit()
                            var_intInseridos += 1
                        else:
                            logger.warning(f"ID_ITAD {var_strIDITAD} não encontrado em itad_raw (pulando)")
                            var_connConnection.rollback()

                except Exception as e:
                    var_connConnection.rollback()
                    logger.error(f"Erro ao atualizar histórico de preços para ID_ITAD {var_strIDITAD}: {e}")
                    continue
            
            logger.info(f"Inseridos {var_intInseridos:,} registros no itad_raw")
            return var_intInseridos
                
        except Exception as e:
            logger.error(f"Erro geral ao inserir dados históricos de preços: {e}")
            return var_intInseridos
        
        finally:
            cls.desconectar(var_connConnection)

    @classmethod
    def inserir_dados_itad_raw_batched(cls, arg_dictDadosItad: dict[int, dict], arg_intBatchSize: int = 1000) -> int:
        """
        Insere dados ITAD em lotes para evitar timeout.
        
        Parâmetros:
        - arg_dictDadosItad (dict): Dicionário mapeando appid -> dados ITAD
        - arg_intBatchSize (int): Tamanho do lote (padrão: 1000)
        
        Retorna:
        - int: Total de registros inseridos/atualizados
        """
        if not arg_dictDadosItad:
            return 0
        
        var_listItems = list(arg_dictDadosItad.items())
        var_intTotal = len(var_listItems)
        var_intInseridosTotal = 0
        
        logger.info(f"Inserindo {var_intTotal:,} registros ITAD em lotes de {arg_intBatchSize}")
        
        for i in range(0, var_intTotal, arg_intBatchSize):
            var_listBatch = var_listItems[i:i + arg_intBatchSize]
            var_dictBatch = dict(var_listBatch)
            
            logger.info(f"Processando lote {i//arg_intBatchSize + 1} ({i+1} a {min(i+arg_intBatchSize, var_intTotal)} de {var_intTotal})")
            var_intInseridos = cls.inserir_dados_itad_raw_bulk(var_dictBatch)
            var_intInseridosTotal += var_intInseridos
            
            # Pausa entre lotes
            if i + arg_intBatchSize < var_intTotal:
                sleep(1)
        
        logger.info(f"Total inserido no ITAD: {var_intInseridosTotal:,} registros")
        return var_intInseridosTotal

    @classmethod
    def buscar_itad_id_por_appid(cls, arg_listAppids: list) -> Generator[str | None, None, None]:
        """
        Busca o ID ITAD correspondente a uma lista de AppIDs Steam.

        Parâmetros:
        - arg_listAppids (list): Lista de AppIDs Steam.

        Retorna:
        - Generator[str | None, None, None]: Generator que produz IDs ITAD correspondentes (um por vez).
                                              Retorna None para AppIDs sem mapeamento ITAD.
        """
        var_connConnection = cls.conectar()
        try:
            for var_intAppid in arg_listAppids:
                var_strSQL = """
                SELECT id_itad FROM steam_itad_mapping WHERE appid = %s;
                """
                # Executa a consulta para cada AppID
                with var_connConnection.cursor() as cursor:
                    cursor.execute(var_strSQL, (var_intAppid,))
                    var_tupleResultado = cursor.fetchone()
                    if var_tupleResultado:
                        # Retorna o ID ITAD encontrado
                        yield var_tupleResultado[0]
                    else:
                        yield None
        except Exception as e:
            logger.error(f"Erro ao buscar IDs ITAD para AppIDs fornecidos: {e}")
            raise Exception(f"Erro ao buscar IDs ITAD para AppIDs fornecidos: {e}")
        finally:
            cls.desconectar(var_connConnection)