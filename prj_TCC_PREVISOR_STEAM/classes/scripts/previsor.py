from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_dados import LimpezaDados

from datetime import datetime
from time import sleep
import json, logging, asyncio, os

from prj_TCC_PREVISOR_STEAM.classes.utils.GetTask import GetTask

logger = logging.getLogger(__name__)

class Previsor:
    """
    Classe responsável por gerenciar módulos gerais do projeto.
    """
    _var_boolUseSupabase = os.getenv("USE_SUPABASE", "false").lower() == "true"

    @classmethod
    def seleciona_games(cls, arg_listDados: list) -> list:
        """
        Seleciona apenas os jogos dos dados fornecidos.
        
        Parâmetros:
        - arg_listDados (list): Lista de dados a serem filtrados.

        Retorna:
        - var_listGames (list): Lista contendo apenas os jogos.
        """
        try:
            var_listGames = []
            for var_dictDado in arg_listDados:
                if var_dictDado.get("detalhes").get("type") == "game" and not var_dictDado.get("detalhes").get("is_free"):
                    var_listGames.append(var_dictDado)
            logger.info(f"Número de jogos pagos selecionados: {len(var_listGames)}")
            return var_listGames
        except Exception as e:
            logger.error(f"Erro ao selecionar jogos: {e}")
            return []
        
    @classmethod
    def selecionar_base_dadosSteamBD(cls, arg_listDados: list) -> dict:
        """
        Seleciona os dados relevantes para a base de dados.
        """
        try:
            var_setCategorias = set()
            var_setGenero = set()
            var_strdataLancamento = ""
            var_listDados = []

            for var_dictApp in arg_listDados:
                # Dados Detalhes
                var_dictDetalhes = var_dictApp.get("detalhes")
                if not var_dictDetalhes:
                    logger.warning("Aplicativo inválido ou vazio encontrado, pulando.")
                    logger.debug(f"Dados do aplicativo: {var_dictApp}")
                    continue

                var_intAppid = int(var_dictDetalhes.get("steam_appid"))
                var_strName = var_dictDetalhes.get("name")
                var_intIdadeClassificada = var_dictDetalhes.get("required_age")
                if var_dictDetalhes.get("ratings") and var_dictDetalhes.get("ratings").get("dejus"):
                    var_strClassificacaoEtaria = var_dictDetalhes.get("ratings").get("dejus").get("rating")
                else:
                    var_strClassificacaoEtaria = None
                var_listLinguagens = var_dictDetalhes.get("supported_languages").replace("<strong>*</strong>", "").replace("<br>", ", ").split(", ")
                var_listDesenvolvedores = var_dictDetalhes.get("developers")
                var_listDistribuidores = var_dictDetalhes.get("publishers")
                var_strPreco = var_dictDetalhes.get("price_overview").get("final_formatted") if var_dictDetalhes.get("price_overview") else None
                var_intMetacriticScore = var_dictDetalhes.get("metacritic").get("score") if var_dictDetalhes.get("metacritic") else None
                for var_dictCategoria in var_dictDetalhes.get("categories"):
                    var_setCategorias.add(var_dictCategoria.get("description"))
                for var_dictGenero in var_dictDetalhes.get("genres"):
                    var_setGenero.add(var_dictGenero.get("description"))
                if var_dictDetalhes.get("release_date").get("date"):
                    var_strdataLancamento = LimpezaDados.tratar_data(arg_strData=var_dictDetalhes.get("release_date").get("date"))
                elif var_dictDetalhes.get("release_date").get("coming_soon"):
                    var_strdataLancamento = "Em breve"
                else:
                    var_strdataLancamento = None
                
                var_listCategorias = list(var_setCategorias)
                var_listGenero = list(var_setGenero)

                # Dados Reviews
                var_dictReviews = var_dictApp.get("reviews")
                var_intReviewScore = int(json.dumps(var_dictReviews.get("review_score"))) if var_dictReviews else None
                var_intTotalReviews = int(json.dumps(var_dictReviews.get("total_reviews"))) if var_dictReviews else None
                var_intTotalNegative = int(json.dumps(var_dictReviews.get("total_negative"))) if var_dictReviews else None
                var_intTotalPositive = int(json.dumps(var_dictReviews.get("total_positive"))) if var_dictReviews else None
                var_strReviewDesc = json.dumps(var_dictReviews.get("review_score_desc")) if var_dictReviews else None

                var_dictDados={
                    "appid": var_intAppid,
                    "nome": var_strName,
                    "idade_classificada": str(var_intIdadeClassificada),
                    "classificacao_etaria": var_strClassificacaoEtaria,
                    "linguagens": var_listLinguagens,
                    "desenvolvedores": var_listDesenvolvedores,
                    "distribuidores": var_listDistribuidores,
                    "preco": var_strPreco,
                    "metacritic_score": str(var_intMetacriticScore),
                    "categorias": var_listCategorias,
                    "genero": var_listGenero,
                    "data_lancamento": var_strdataLancamento,
                    "review_score": var_intReviewScore,
                    "total_reviews": var_intTotalReviews,
                    "total_negative": var_intTotalNegative,
                    "total_positive": var_intTotalPositive,
                    "review_score_desc": var_strReviewDesc,
                }
                var_listDados.append(var_dictDados)
            return var_listDados
        
        except Exception as e:
            logger.error(f"Erro ao selecionar base de dados Steam BD: {e}")
            return []
        
    @classmethod
    def selecionar_dados_velhos(cls, arg_listDados: list, arg_strNomeTabela: str) -> dict:
        """
        Seleciona os dados que tiveram sua última atualização anterior a um determinado período.

        Parâmetros:
        - arg_listDados (list): Lista de dados a serem processados.
        - arg_strNomeTabela (str): Nome da tabela para verificação de última atualização.

        Retorna:
        - var_listDados (list): Lista contendo os dados processados.
        """
        try:
            var_listDados = []

            for var_dictApp in arg_listDados:
                if var_dictApp.get("appid"):
                    if cls._var_boolUseSupabase:
                        var_dateUltimaAtualizacao = SupabaseDB.buscar_jogos_por_ID(arg_intAppid=var_dictApp.get("appid"), arg_strNomeTabela=arg_strNomeTabela)
                    else:
                        var_dateUltimaAtualizacao = PostgreSQL.verificar_ultima_atualizacao(arg_intAppid=var_dictApp.get("appid"), arg_strNomeTabela=arg_strNomeTabela)
                    
                    if var_dateUltimaAtualizacao:
                        var_intDiasDesdeAtualizacao = (datetime.now().replace(tzinfo=None) - var_dateUltimaAtualizacao.replace(tzinfo=None)).days
                    else:
                        var_intDiasDesdeAtualizacao = Settings._var_dictSettings["dias_para_atualizacao"] + 1

                    if var_intDiasDesdeAtualizacao < Settings._var_dictSettings["dias_para_atualizacao"]:
                        continue
                    var_listDados.append(var_dictApp.get("appid"))
            if not var_listDados:
                logger.info("Nenhum dado antigo encontrado para atualização.")
            return var_listDados
        
        except Exception as e:
            logger.error(f"Erro ao selecionar dados antigos: {e}")
            return []
        
    @classmethod
    def alimentar_banco_dados_raw(cls):
        """
        Alimenta o banco de dados raiz com os dados coletados da API.

        Parâmetros:
        
        Retorna:
        - None
        """
        try:
            var_listApp = GetTask.load_task_queue()
            var_intRange = 500  # Processa 500 AppIDs por vez (ajustável)
            var_listApp = var_listApp[len(var_listApp)//2:(len(var_listApp)//2)+var_intRange]  # Processa apenas a segunda metade da lista para testes
            # Itera sobre os aplicativos em lotes
            for i in range(0, len(var_listApp), var_intRange):
                var_listAppAtual = var_listApp[i:i+var_intRange]
                var_listAppIDAtual = [var_listAppAtual[j]['appid'] for j in range(len(var_listAppAtual))]
                
                # Verifica quais AppIDs já estão no banco de dados
                var_listAppIDnoBD = SupabaseDB.buscar_jogos_por_ID(arg_listAppIDs=var_listAppIDAtual, arg_strNomeTabel="steam_raw")
                var_listAppIDDesatualizado = SupabaseDB.buscar_jogos_desatualizados(arg_intLimite=var_intRange)
                for var_dictAppID in var_listAppIDnoBD:
                    var_intAppID = var_dictAppID['appid']
                    if var_intAppID in var_listAppIDAtual:
                        var_listAppIDAtual.remove(var_intAppID)

                for var_dictAppID in var_listAppIDDesatualizado:
                    var_intAppID = var_dictAppID['appid']
                    if var_intAppID not in var_listAppIDAtual:
                        var_listAppIDAtual.append(var_intAppID)

                if not var_listAppIDAtual:
                    logger.info("Nenhum AppID encontrado para atualização nesta iteração.")
                    continue

                logger.info(f"Número de AppIDs a processar: {len(var_listAppIDAtual)}")

                # Busca detalhes dos jogos
                var_dictDetails = asyncio.run(SteamClient.fetch_details_bulk_batched(arg_seqAppids=var_listAppIDAtual))
                if not var_dictDetails:
                    logger.warning("Nenhum dado de detalhes retornado da API Steam.")
                else:
                    for var_intAppid in var_dictDetails.keys():
                        var_dictRawData = {
                            "appid": var_intAppid,
                            "detalhes": var_dictDetails.get(var_intAppid),
                        }
                        
                        SupabaseDB.inserir_dadosSteamRaw(var_dictRawData)    
                    logger.info("Dados de detalhes inseridos com sucesso.")

                    sleep(1800)  # Espera 30 minutos entre os testes para evitar bloqueios

                # Busca reviews dos jogos
                var_dictReview = asyncio.run(SteamClient.fetch_reviews_summary_batched(arg_seqAppids=var_listAppIDAtual))
                if not var_dictReview:
                    logger.warning("Nenhum dado de reviews retornado da API Steam.")
                else:
                    # Combina reviews
                    for var_intAppid in var_dictDetails.keys():
                        var_dictRawData = {
                            "appid": var_intAppid,
                            "reviews": var_dictReview.get(var_intAppid)
                        }
                        
                        SupabaseDB.inserir_dadosSteamRaw(var_dictRawData)    
                    logger.info("Dados de reviews inseridos com sucesso.")
            
        except Exception as e:
            logger.error(f"Erro ao alimentar o banco de dados: {e}")
            raise Exception(f"Erro ao alimentar o banco de dados: {e}")
        
    @classmethod
    def alimentar_banco_dados_Steam(cls):
        """
        Alimenta o banco de dados Steam BD com os dados processados do steam_raw.
        
        Parâmetros:
        
        Retorna:
        - None
        """
        try:
            
            # Processa dados para steam_bd
            var_listDadosSteamRaw = SupabaseDB.buscar_todos_dadosSteamRaw(arg_intLimit=300000)
                
            var_listGames = cls.seleciona_games(var_listDadosSteamRaw)
            if var_listGames:
                var_listDados = cls.selecionar_base_dadosSteamBD(var_listGames)
                var_listDadosVelhos = cls.selecionar_dados_velhos(arg_listDados=var_listDados, arg_strNomeTabela="steam_bd")
                for var_intAppID in var_listDadosVelhos:
                    SupabaseDB.inserir_dadosSteamBD(var_listDados[var_intAppID])
                logger.info("Dados processados inseridos na tabela steam_bd com sucesso.")
            else:
                raise Exception("Nenhum jogo válido encontrado para processar.")

        except Exception as e:
            logger.error(f"Erro ao alimentar o banco de dados Steam BD: {e}")
            raise Exception(f"Erro ao alimentar o banco de dados Steam BD: {e}")