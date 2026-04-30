from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_generico import PostgreSQL

from psycopg2.extras import execute_batch, execute_values
import json, logging

logger = logging.getLogger(__name__)

class PostgreSQLBDGeral(PostgreSQL):
    """
    Classe para operações com PostgreSQL.
    """
    
    @classmethod
    def buscar_dados_Geral_por_appid(cls, arg_listAppIDs: list) -> dict:
        """
        Busca dados de jogos na tabela steam_unificado com base em uma lista de AppIDs.

        Parâmetros:
        - arg_listAppIDs (list): Lista de AppIDs para buscar.

        Retorna:
        - list[dict]: Lista de dicionários com os dados dos jogos encontrados.
        """
        try:
            var_strSQL = """
            SELECT 
                    su.appid, 
                    su.nome,
                    su.classificacao_etaria,
                    su.linguagens,
                    su.desenvolvedores,
                    su.distribuidores,
                    su.preco,
                    su.categorias,
                    su.genero,
                    su.data_lancamento,
                    su.review_score,
                    su.total_reviews,
                    su.total_negative,
                    su.total_positive,
                    su.review_score_desc
            FROM steam_unificado su
            WHERE appid = ANY(%s)
            AND type = 'game';
            """
            var_connConnection = cls.conectar()
            with var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, (arg_listAppIDs,))
                var_listResultados = cursor.fetchall()
                var_listDados = []
                for row in var_listResultados:
                    var_dictDetalhes = None
                    if row[1] and row[1] not in ("AUSENTE", "ausente"):
                        try:
                            var_dictDetalhes = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"AppID {row[0]}: Erro ao parsear detalhes como JSON - {e}")
                            var_dictDetalhes = "AUSENTE"
                    else:
                        var_dictDetalhes = "AUSENTE"
                    
                    var_dictReviews = None
                    if row[2] and row[2] not in ("AUSENTE", "ausente"):
                        try:
                            var_dictReviews = json.loads(row[2]) if isinstance(row[2], str) else row[2]
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"AppID {row[0]}: Erro ao parsear reviews como JSON - {e}")
                            var_dictReviews = None
                    
                    var_dictDados = {
                        "appid": row[0],
                        "detalhes": var_dictDetalhes,
                        "reviews": var_dictReviews
                    }
                    var_listDados.append(var_dictDados)
                return var_listDados
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados por AppIDs: {e}")
            raise Exception(f"Erro ao buscar dados por AppIDs: {e}")
        finally:
            if var_connConnection:
                cls.desconectar(var_connConnection)

    @classmethod
    def buscar_dados_Geral(cls, arg_strFiltro: str = None, arg_boolFiltroPadrao: bool = False) -> list:
        """
        Busca dados na tabela steam_geral.

        Parâmetros:
        - arg_strFiltro (str): Filtro opcional para a consulta SQL. Exemplo: "preco != 'Grátis'".
        
        Retorna:
        - list[dict]: Lista de dicionários com os dados dos jogos.
        """
        var_connConnection = cls.conectar()
        
        try:
            var_strSQLGeral = """
            SELECT
                su.appid, 
                sim.id_itad, 
                su.nome, 
                su.classificacao_etaria, 
                su.linguagens, 
                su.desenvolvedores, 
                su.distribuidores, 
                su.preco, 
                su.categorias, 
                su.genero, 
                su.data_lancamento, 
                su.review_score, 
                su.total_reviews, 
                su.total_negative, 
                su.total_positive, 
                su.review_score_desc, 
                ir.historico_preco
            FROM steam_unificado su
            INNER JOIN steam_itad_mapping sim ON su.appid = sim.appid
            INNER JOIN itad_raw ir ON sim.id_itad = ir.id_itad
            """

            if arg_boolFiltroPadrao:
                var_strSQLGeral += f"""
                WHERE su.type = 'game' 
                    AND su.preco <> 'Gratuito' 
                    AND sim.id_itad IS NOT NULL 
                    AND sim.id_itad NOT IN ('', 'AUSENTE')
                    AND ir.historico_preco IS NOT NULL
                    """
            else:
                if arg_strFiltro:
                    var_strSQLGeral += f"""
                    WHERE {arg_strFiltro}
                    """

            var_strSQLGeral += "ORDER BY su.appid;"

            with var_connConnection.cursor() as var_curCursor:
                var_curCursor.execute(var_strSQLGeral)
                var_listResultados = var_curCursor.fetchall()
                var_listColnames = [desc[0] for desc in var_curCursor.description]
                var_listDados = [dict(zip(var_listColnames, row)) for row in var_listResultados]

            logger.info(f"Dados buscados com sucesso da tabela steam_geral. Total de registros: {len(var_listDados)}")
            return var_listDados

        except Exception as err:
            logger.error(f"Erro ao buscar dados steam_geral: {err}")
            raise Exception(f"Erro ao buscar dados em steam_geral: {err}")
        finally:
            if var_connConnection:
                cls.desconectar(var_connConnection)

    @classmethod
    def inserir_dados_Geral_Bulk(cls, arg_listDados:list) -> None:
        """
        Busca e insere ou atualiza dados em bulk na tabela steam_geral.

        Parâmetros:
        - arg_listDados (list[dict]): Lista de dicionários com os dados dos jogos a serem inseridos ou atualizados.
        """
        var_connConnection = cls.conectar()
        try:
            var_strSQLInsert = """
            INSERT INTO steam_geral (
                appid, id_itad, nome, classificacao_etaria, linguagens, desenvolvedores, distribuidores, preco, categorias, genero, data_lancamento, review_score, total_reviews, total_negative, total_positive, review_score_desc, historico_precos
            ) VALUES %s
            ON CONFLICT (appid) DO UPDATE SET
                id_itad = EXCLUDED.id_itad,
                nome = EXCLUDED.nome,
                classificacao_etaria = EXCLUDED.classificacao_etaria,
                linguagens = EXCLUDED.linguagens,
                desenvolvedores = EXCLUDED.desenvolvedores,
                distribuidores = EXCLUDED.distribuidores,
                preco = EXCLUDED.preco,
                categorias = EXCLUDED.categorias,
                genero = EXCLUDED.genero,
                data_lancamento = EXCLUDED.data_lancamento,
                review_score = EXCLUDED.review_score,
                total_reviews = EXCLUDED.total_reviews,
                total_negative = EXCLUDED.total_negative,
                total_positive = EXCLUDED.total_positive,
                review_score_desc = EXCLUDED.review_score_desc,
                historico_precos = EXCLUDED.historico_precos,
                ultima_atualizacao = CURRENT_TIMESTAMP;
            """
            
            var_listValores = []
            for var_dictDado in arg_listDados:

                var_listValores.append((
                    var_dictDado.get("appid"),
                    var_dictDado.get("id_itad"),
                    var_dictDado.get("nome"),
                    var_dictDado.get("classificacao_etaria"),
                    var_dictDado.get("linguagens"),
                    var_dictDado.get("desenvolvedores"),
                    var_dictDado.get("distribuidores"),
                    var_dictDado.get("preco"),
                    var_dictDado.get("categorias"),
                    var_dictDado.get("genero"),
                    var_dictDado.get("data_lancamento"),
                    var_dictDado.get("review_score"),
                    var_dictDado.get("total_reviews"),
                    var_dictDado.get("total_negative"),
                    var_dictDado.get("total_positive"),
                    var_dictDado.get("review_score_desc"),
                    json.dumps(var_dictDado.get("historico_precos", []))
                ))
            with var_connConnection.cursor() as var_curCursor:
                execute_values(var_curCursor, var_strSQLInsert, var_listValores)
                var_connConnection.commit()

        except Exception as err:
            logger.error(f"Erro ao inserir dados steam_geral: {err}")
            if var_connConnection:
                var_connConnection.rollback()
            raise Exception(f"Erro ao inserir dados em bulk em steam_geral: {err}")
        finally:
            if var_connConnection:
                cls.desconectar(var_connConnection)