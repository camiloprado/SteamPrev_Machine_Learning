from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_dados import LimpezaDados

from datetime import datetime
import json, logging

logger = logging.getLogger(__name__)

class Previsor:
    """
    Classe responsável por gerenciar módulos gerais do projeto.
    """

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
                    "reviews": json.dumps(var_dictApp.get("reviews"))
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