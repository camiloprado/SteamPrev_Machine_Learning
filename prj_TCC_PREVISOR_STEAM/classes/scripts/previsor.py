from prj_TCC_PREVISOR_STEAM.classes.SQL.supabase_db import SupabaseDB
from prj_TCC_PREVISOR_STEAM.classes.api.steam_api import SteamClient
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_dados import LimpezaDados

from datetime import datetime
from time import sleep
import json, logging, asyncio, os
from typing import Dict, Any

from prj_TCC_PREVISOR_STEAM.classes.utils.GetTask import GetTask

logger = logging.getLogger(__name__)

class Previsor:
    """
    Classe responsável por gerenciar módulos gerais do projeto.
    """
    _var_boolUseSupabase = os.getenv("USE_SUPABASE", "false").lower() == "true"
    _var_intTamanhoTotalFila = 0

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

                if var_dictDetalhes.get("ratings") and var_dictDetalhes.get("ratings").get("dejus"):
                    var_strClassificacaoEtaria = var_dictDetalhes.get("ratings").get("dejus").get("rating")
                else:
                    var_strClassificacaoEtaria = "l"

                if var_dictDetalhes.get("supported_languages"):
                    var_listLinguagens = var_dictDetalhes.get("supported_languages").replace("<strong>*</strong>", "").replace("<br>", ", ").split(", ")
                else:
                    var_listLinguagens = []

                if var_dictDetalhes.get("developers"):
                    var_listDesenvolvedores = var_dictDetalhes.get("developers")
                else:
                    var_listDesenvolvedores = []

                if var_dictDetalhes.get("publishers"):
                    var_listDistribuidores = var_dictDetalhes.get("publishers")
                else:
                    var_listDistribuidores = []

                var_strPreco = var_dictDetalhes.get("price_overview").get("final_formatted") if var_dictDetalhes.get("price_overview") else 0
                var_intMetacriticScore = var_dictDetalhes.get("metacritic").get("score") if var_dictDetalhes.get("metacritic") else 0
                
                if var_dictDetalhes.get("categories"):
                    for var_dictCategoria in var_dictDetalhes.get("categories"):
                        var_setCategorias.add(var_dictCategoria.get("description"))
                
                if var_dictDetalhes.get("genres"):
                    for var_dictGenero in var_dictDetalhes.get("genres"):
                        var_setGenero.add(var_dictGenero.get("description"))

                if not var_dictDetalhes.get("release_date").get("coming_soon"):
                    if var_dictDetalhes.get("release_date").get("date"):
                        var_strdataLancamento = LimpezaDados.tratar_data(arg_strData=var_dictDetalhes.get("release_date").get("date"))
                    else:
                        var_strdataLancamento = None
                else:
                    var_strdataLancamento = "Em Breve"

                var_listCategorias = list(var_setCategorias)
                var_listGenero = list(var_setGenero)

                # Dados Reviews
                var_dictReviews = var_dictApp.get("reviews")
                var_intReviewScore = int(json.dumps(var_dictReviews.get("review_score"))) if var_dictReviews else 0
                var_intTotalReviews = int(json.dumps(var_dictReviews.get("total_reviews"))) if var_dictReviews else 0
                var_intTotalNegative = int(json.dumps(var_dictReviews.get("total_negative"))) if var_dictReviews else 0
                var_intTotalPositive = int(json.dumps(var_dictReviews.get("total_positive"))) if var_dictReviews else 0
                var_strReviewDesc = json.dumps(var_dictReviews.get("review_score_desc")) if var_dictReviews else None

                var_dictDados={
                    "appid": var_intAppid,
                    "nome": var_strName,
                    "classificacao_etaria": var_strClassificacaoEtaria,
                    "linguagens": var_listLinguagens,
                    "desenvolvedores": var_listDesenvolvedores,
                    "distribuidores": var_listDistribuidores,
                    "preco": var_strPreco,
                    "metacritic_score": var_intMetacriticScore,
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
    def alimentar_banco_dados_raw(cls):
        """
        Alimenta o banco de dados raiz com os dados coletados da API.

        Parâmetros:
        
        Retorna:
        - None
        """
        try:
            var_listApp = GetTask.load_task_queue()
            cls._var_intTamanhoTotalFila = len(var_listApp)
            var_intRange = 2000  # Processa x AppIDs por vez (ajustável)
            var_listApp = var_listApp[1000:1005]  # Para testes rápidos, remove essa linha na produção
            # Itera sobre os aplicativos em lotes
            for i in range(0, len(var_listApp), var_intRange):
                logger.info(f"Processando aplicativos de {i + 1} a {min(i + var_intRange, len(var_listApp))} de {len(var_listApp)}")
                var_listAppAtual = var_listApp[i:i+var_intRange]
                var_listAppIDAtual = [var_listAppAtual[j]['appid'] for j in range(len(var_listAppAtual))]
                
                # Verifica quais AppIDs já estão no banco de dados
                var_listAppIDnoBD = SupabaseDB.buscar_jogos_por_ID(arg_listAppIDs=var_listAppIDAtual, arg_strNomeTabel="steam_raw")
                var_listAppIDDesatualizado = SupabaseDB.buscar_jogos_desatualizados()
                var_listAppIDIncompleto = SupabaseDB.buscar_jogos_incompletos(arg_boolRequererReviews=True)

                for var_dictAppID in var_listAppIDnoBD:
                    var_intAppID = var_dictAppID['appid']
                    if var_intAppID in var_listAppIDAtual:
                        var_listAppIDAtual.remove(var_intAppID)

                for var_dictAppID in var_listAppIDDesatualizado:
                    var_intAppID = var_dictAppID['appid']
                    if var_intAppID not in var_listAppIDAtual:
                        var_listAppIDAtual.append(var_intAppID)
                
                if var_listAppIDIncompleto:
                    for var_dictAppID in var_listAppIDIncompleto:
                        var_intAppID = var_dictAppID['appid']
                        if var_dictAppID.get('detalhes') is None:
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

                if var_listAppIDIncompleto:
                    logger.info(f"Número de AppIDs com dados incompletos: {len(var_listAppIDIncompleto)}")
                    for var_dictAppID in var_listAppIDIncompleto:
                        var_intAppID = var_dictAppID['appid']
                        if var_dictAppID.get('reviews') is None:
                            if var_intAppID not in var_listAppIDAtual:
                                var_listAppIDAtual.append(var_intAppID)

                # Busca reviews dos jogos
                var_dictReview = asyncio.run(SteamClient.fetch_reviews_summary_batched(arg_seqAppids=var_listAppIDAtual))
                if not var_dictReview:
                    logger.warning("Nenhum dado de reviews retornado da API Steam.")
                else:
                    # Combina reviews
                    for var_intAppid in var_dictReview.keys():
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
            var_listDadosSteamRaw = SupabaseDB.buscar_todos_dadosSteamRaw()
            var_listGames = cls.seleciona_games(var_listDadosSteamRaw)
            if var_listGames:
                var_listDados = cls.selecionar_base_dadosSteamBD(var_listGames)
                var_intRange = 3000  # Insere x registros por vez (ajustável)
                # Insere em lotes
                for i in range(0, len(var_listDados), var_intRange):
                    logger.info(f"Inserindo registros de {i + 1} a {min(i + var_intRange, len(var_listDados))} de {len(var_listDados)} na tabela steam_bd")
                    var_listDadosParcial = var_listDados[i:i+var_intRange]
                    for var_intTentativa in range(3):  # Tenta 3 vezes em caso de falha
                        try:
                            SupabaseDB.inserir_dadosSteamBD(var_listDadosParcial)
                            break  # Sai do loop se a inserção for bem-sucedida
                        except Exception as e:
                            logger.error(f"Erro ao inserir dados na tentativa {var_intTentativa + 1}: {e}")
                            if var_intTentativa < 2:
                                sleep(5)  # Espera 5 segundos antes de tentar novamente
                            else:
                                raise  # Relevanta a exceção após 3 tentativas

                logger.info("Dados processados inseridos na tabela steam_bd com sucesso.")
            else:
                raise Exception("Nenhum jogo válido encontrado para processar.")

        except Exception as e:
            logger.error(f"Erro ao alimentar o banco de dados Steam BD: {e}")
            raise Exception(f"Erro ao alimentar o banco de dados Steam BD: {e}")
        
    @classmethod
    def alimentar_banco_dados_ITAD(cls):
        """
        Alimenta o banco de dados com dados do ITAD.
        
        Parâmetros:
        
        Retorna:
        - None
        """
        try:
            var_listDadosSteamRaw = SupabaseDB.buscar_todos_dadosSteamBD()
            var_listDadosSteamRaw = var_listDadosSteamRaw[0:5]  # Para testes rápidos, remover na produção
            var_intTamanhoTotalFila = len(var_listDadosSteamRaw)
            var_intRange = 2000  # Processa x AppIDs por vez (ajustável)
            
            # Itera sobre os aplicativos em lotes
            for i in range(0, var_intTamanhoTotalFila, var_intRange):
                logger.info(f"Processando aplicativos de {i + 1} a {min(i + var_intRange, var_intTamanhoTotalFila)} de {var_intTamanhoTotalFila}")
                var_listAppAtual = var_listDadosSteamRaw[i:i+var_intRange]
                var_listAppIDAtual = [var_listAppAtual[j]['appid'] for j in range(len(var_listAppAtual))]
                
                var_listAppIDDesatualizado = SupabaseDB.buscar_jogos_desatualizados(arg_strNomeTabela="itad_raw")
                
                for var_dictAppID in var_listAppIDDesatualizado:
                    var_intAppID = var_dictAppID['appid']
                    if var_intAppID not in var_listAppIDAtual:
                        var_listAppIDAtual.append(var_intAppID)
                
                if not var_listAppIDAtual:
                    logger.info("Nenhum AppID encontrado para atualização nesta iteração.")
                    continue

                logger.info(f"Número de IDs a processar: {len(var_listAppIDAtual)}")

                # Busca detalhes dos jogos
                var_listDetails = SteamClient.lookup_itad_ids(arg_seqAppids=var_listAppIDAtual)
                if not var_listDetails:
                    logger.warning("Nenhum dado de detalhes retornado da API Steam.")
                else:
                    for var_dictITAD in var_listDetails:

                        var_dictRawData = {
                            "id": var_dictITAD.get("id"),
                            "slug": var_dictITAD.get("slug"),
                            "title": var_dictITAD.get("title"),
                            "type": var_dictITAD.get("type"),
                            "mature": var_dictITAD.get("mature"),
                            "assets": var_dictITAD.get("assets"),
                            "ultima_atualizacao": datetime.now().isoformat(),
                        }
                        
                        SupabaseDB.inserir_dadosSteamRaw(var_dictRawData)    
                    logger.info("Dados de detalhes inseridos com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao alimentar o banco de dados ITAD: {e}")
            raise Exception(f"Erro ao alimentar o banco de dados ITAD: {e}")
        
    # ================ AUSENTES ================
    @staticmethod
    def criar_reviews_padrao(arg_intAppid: int, arg_strMotivo: str = "Sem reviews disponíveis") -> Dict[str, Any]:
        """
        Cria um dicionário de reviews com valores padrão.
        
        Parâmetros:
        - arg_intAppid (int): AppID do jogo
        - arg_strMotivo (str): Motivo da ausência de reviews
        
        Retorna:
        - dict: Dicionário com estrutura de reviews padrão
        """
        var_dictReviewsPadrao = {
            "appid": arg_intAppid,
            "total_reviews": 0,
            "total_positive": 0,
            "total_negative": 0,
            "review_score": 0,
            "review_score_desc": arg_strMotivo,
            "_padrao": True,  # Flag para identificar dados padrão
            "_motivo": arg_strMotivo
        }
        
        logger.debug(f"AppID {arg_intAppid}: Reviews preenchidos com valores padrão - {arg_strMotivo}")
        return var_dictReviewsPadrao
    
    @classmethod
    def preencher_se_ausente(cls, arg_dictDados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preenche reviews com valores padrão se estiverem ausentes.
        
        Parâmetros:
        - arg_dictDados (dict): Dicionário com dados do jogo (pode ou não ter 'reviews')
        
        Retorna:
        - dict: Dicionário com reviews garantidos (originais ou padrão)
        """
        var_intAppid = arg_dictDados.get("appid")
        
        # Se já tem reviews válidos, retorna como está
        if "reviews" in arg_dictDados and arg_dictDados["reviews"] is not None:
            var_dictReviews = arg_dictDados["reviews"]
            # Verifica se tem pelo menos total_reviews
            if isinstance(var_dictReviews, dict) and "total_reviews" in var_dictReviews:
                return arg_dictDados
        
        # Se não tem reviews, preenche com padrão
        arg_dictDados["reviews"] = cls.criar_reviews_padrao(
            var_intAppid,
            "API Steam não retornou reviews"
        )
        
        return arg_dictDados
    
    @classmethod
    def processar_lote(cls, arg_listDados: list) -> list:
        """
        Processa um lote de dados, preenchendo reviews ausentes.
        
        Parâmetros:
        - arg_listDados (list): Lista de dicionários com dados de jogos
        
        Retorna:
        - list: Lista processada com reviews garantidos
        """
        var_intTotal = len(arg_listDados)
        var_intPreenchidos = 0
        
        var_listProcessados = []
        for var_dictDado in arg_listDados:
            var_boolTemReviews = "reviews" in var_dictDado and var_dictDado["reviews"] is not None
            
            var_dictProcessado = cls.preencher_se_ausente(var_dictDado)
            var_listProcessados.append(var_dictProcessado)
            
            if not var_boolTemReviews:
                var_intPreenchidos += 1
        
        if var_intPreenchidos > 0:
            logger.info(f"Reviews padrão: {var_intPreenchidos}/{var_intTotal} jogos ({var_intPreenchidos/var_intTotal:.1%})")
        
        return var_listProcessados
