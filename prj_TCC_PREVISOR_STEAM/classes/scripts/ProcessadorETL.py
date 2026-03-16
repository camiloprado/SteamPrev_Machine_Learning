from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_steam import PostgreSQLSteam
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza import Limpar
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_nome import LimparNome
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_idade import LimparIdade
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_linguagens import LimparLinguagens
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_desenvolvedor import LimparDesenvolvedor
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_distribuidores import LimparDistribuidores
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_preco import LimparPreco
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_metacritic import LimparMetacritic
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_categoria import LimparCategoria
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_genero import LimparGenero
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_data_lancamento import LimparDataLancamento

from typing import List, Dict, Any
import re, logging
import unicodedata
from datetime import datetime

logger = logging.getLogger(__name__)

class ProcessadorETL:
    """
    Classe para processar dados brutos (steam_raw) em dados estruturados (steam_bd)
    """
    
    @staticmethod
    def transformar_raw_para_bd(arg_dictDadosRaw: Dict) -> Dict:
        """
        Transforma dados brutos em dados estruturados
        
        Parametros:
        - arg_dictDadosRaw (dict): Dicionário com steam_appid, detalhes, reviews
        
        Retorna:
        - dict: Dicionário estruturado para steam_bd
        """
        # Validação inicial: verifica se há dados
        if not arg_dictDadosRaw:
            raise ValueError("Dicionário de dados está vazio")
        
        # Tenta pegar appid de diferentes campos possíveis
        var_intAppid = arg_dictDadosRaw.get("appid")
        
        # Validação: AppID deve existir
        if not var_intAppid:
            raise ValueError("AppID não encontrado nos dados brutos")
        
        # Extrai detalhes e reviews
        var_dictDetalhes = arg_dictDadosRaw.get("detalhes")
        var_dictReviews = arg_dictDadosRaw.get("reviews", {})
        
        # Validação crítica: detalhes não podem ser None ou "AUSENTE"
        if var_dictDetalhes is None or var_dictDetalhes == "AUSENTE" or not isinstance(var_dictDetalhes, dict):
            raise ValueError(f"Detalhes ausentes para AppID {var_intAppid}")
        
        # Se detalhes está vazio, tenta extrair do próprio arg_dictDadosRaw
        if not var_dictDetalhes:
            # Alguns registros podem ter detalhes diretamente no dicionário principal
            if "name" in arg_dictDadosRaw:
                var_dictDetalhes = arg_dictDadosRaw
            else:
                raise ValueError(f"Detalhes vazios para AppID {var_intAppid}")
        var_dictDadosTransformados = {}
        var_dictDadosTransformados['appid'] = var_intAppid
        
        # Nome: normaliza e trunca em 255 caracteres (limite do PostgREST)
        var_strNome = Limpar.extrair_campo_seguro(var_dictDetalhes, "name", arg_anyPadrao="Desconhecido")
        var_dictDadosTransformados["nome"] = LimparNome.normalizar_nome(var_strNome)
        
        var_intClassificacaoEtaria = int(Limpar.extrair_campo_seguro(var_dictDetalhes, "required_age", arg_anyPadrao=0))
        var_dictDadosTransformados["classificacao_etaria"] = LimparIdade.processar_classificacao_etaria(var_intClassificacaoEtaria)

        var_strLinguagensSuportadas = Limpar.extrair_campo_seguro(var_dictDetalhes, "supported_languages", arg_anyPadrao="")
        var_dictDadosTransformados['linguagens'] = LimparLinguagens.processar_linguagens_completo(var_strLinguagensSuportadas)
        
        var_listDesenvolvedores = Limpar.extrair_campo_seguro(var_dictDetalhes, "developers", arg_anyPadrao=[])
        var_dictDadosTransformados["desenvolvedores"] = LimparDesenvolvedor.limpar_desenvolvedor(var_listDesenvolvedores)
        
        var_listDistribuidores = Limpar.extrair_campo_seguro(var_dictDetalhes, "publishers", arg_anyPadrao=[])
        var_dictDadosTransformados["distribuidores"] = LimparDistribuidores.limpar_distribuidores(var_listDistribuidores) 
                
        var_boolFree = Limpar.extrair_campo_seguro(var_dictDetalhes, "is_free", arg_anyPadrao=False)
        if var_boolFree:
            var_dictDadosTransformados["preco"] = "Gratuito"
            var_dictDadosTransformados["metacritic_score"] = "Desconhecido"
        else:
            var_dictPreco = Limpar.extrair_campo_seguro(var_dictDetalhes, "price_overview", arg_anyPadrao={})
            var_dictDadosTransformados["preco"] = LimparPreco.processar_preco(var_dictPreco)

            var_dictMetacritic = Limpar.extrair_campo_seguro(var_dictDetalhes, "metacritic", arg_anyPadrao={})
            var_dictDadosTransformados["metacritic_score"] = LimparMetacritic.processar_metacritic(var_dictMetacritic)

        var_dictCategoria = Limpar.extrair_campo_seguro(var_dictDetalhes, "categories", arg_anyPadrao=[])
        var_dictDadosTransformados['categorias'] = LimparCategoria.processar_categoria_completo(var_dictCategoria)

        var_dictGenero = Limpar.extrair_campo_seguro(var_dictDetalhes, "genres", arg_anyPadrao=[])
        var_dictDadosTransformados["genero"] = LimparGenero.processar_genero_completo(var_dictGenero)

        var_dictDataLancamento = Limpar.extrair_campo_seguro(var_dictDetalhes, "release_date", arg_anyPadrao="")
        var_dictDadosTransformados["data_lancamento"] = LimparDataLancamento.processar_data_lancamento(var_dictDataLancamento)

        var_intReviewScore = Limpar.extrair_campo_seguro(var_dictReviews, "review_score", arg_anyPadrao=0)
        var_intReviewTotal = Limpar.extrair_campo_seguro(var_dictReviews, "total_reviews", arg_anyPadrao=0)
        var_intReviewPositive = Limpar.extrair_campo_seguro(var_dictReviews, "total_positive", arg_anyPadrao=0)
        var_intReviewNegative = Limpar.extrair_campo_seguro(var_dictReviews, "total_negative", arg_anyPadrao=0)
        var_strReviewScoreDesc = Limpar.extrair_campo_seguro(var_dictReviews, "review_score_desc", arg_anyPadrao="")

        var_dictDadosTransformados['review_score'] =  var_intReviewScore if isinstance(var_intReviewScore, int) and 0 <= var_intReviewScore <= 100 else "Desconhecido"
        var_dictDadosTransformados["total_reviews"] = var_intReviewTotal if isinstance(var_intReviewTotal, int) and var_intReviewTotal >= 0 else "Desconhecido"
        var_dictDadosTransformados["total_negative"] = var_intReviewNegative if isinstance(var_intReviewNegative, int) and var_intReviewNegative >= 0 else "Desconhecido"
        var_dictDadosTransformados["total_positive"] = var_intReviewPositive if isinstance(var_intReviewPositive, int) and var_intReviewPositive >= 0 else "Desconhecido"
        var_dictDadosTransformados["review_score_desc"] = Limpar.normalizar_texto(var_strReviewScoreDesc)
        
        # Extrai o tipo do jogo (game, dlc, bundle, etc)
        var_strType = Limpar.extrair_campo_seguro(var_dictDetalhes, "type", arg_anyPadrao="game")
        var_dictDadosTransformados["type"] = var_strType if var_strType else "Desconhecido"
        
        return var_dictDadosTransformados
    
    @staticmethod
    def transformar_raw_para_unificado(arg_dictDadosRaw: Dict) -> Dict:
        """
        Transforma dados brutos em formato para steam_unificado.
        Combina dados estruturados + mantém JSONB completo.
        
        Parâmetros:
        - arg_dictDadosRaw (dict): Dicionário com appid, detalhes, reviews
        
        Retorna:
        - dict: Dicionário estruturado para steam_unificado
        """
        # Primeiro transforma usando o método existente
        var_dictDadosEstruturados = ProcessadorETL.transformar_raw_para_bd(arg_dictDadosRaw)
        
        # Adiciona os campos JSONB completos
        var_dictDadosEstruturados['detalhes_completos'] = arg_dictDadosRaw.get('detalhes')
        var_dictDadosEstruturados['reviews_completos'] = arg_dictDadosRaw.get('reviews')
        
        return var_dictDadosEstruturados
    
    @staticmethod
    def processar_lote_unificado(arg_listAppIDs: list = None) -> None:
        """
        Processa um lote de AppIDs do Docker para steam_unificado.
        Versão consolidada que mantém dados estruturados + JSONB.
        
        Parâmetros:
        - arg_listAppIDs (list, optional): Lista de AppIDs para processar. Se None, processa todos os dados.
        """
        if arg_listAppIDs is None:
            # Buscar dados brutos do Docker
            var_listDados = PostgreSQL.buscar_todos_dados(arg_strNomeTabela="steam_raw")
        else:
            # Buscar dados brutos para os AppIDs especificados
            var_listDados = PostgreSQLSteam.buscar_dados_por_appids(arg_listAppIDs)
        
        logger.info(f"{len(var_listDados)} jogos encontrados no Docker.")
        
        # Transformar dados
        var_listDadosUnificados = []
        var_intErrosTransformacao = 0
        var_dictContagemErros = {
            'detalhes_ausentes': 0,
            'appid_invalido': 0,
            'dados_vazios': 0,
            'outros': 0
        }
        
        for var_dictDadosRaw in var_listDados:
            try:
                var_dictDadosUnificado = ProcessadorETL.transformar_raw_para_unificado(var_dictDadosRaw)
                var_listDadosUnificados.append(var_dictDadosUnificado)
            except ValueError as e:
                var_intErrosTransformacao += 1
                var_strErro = str(e).lower()
                
                # Categoriza o erro
                if 'detalhes ausentes' in var_strErro or 'detalhes vazios' in var_strErro:
                    var_dictContagemErros['detalhes_ausentes'] += 1
                elif 'appid' in var_strErro:
                    var_dictContagemErros['appid_invalido'] += 1
                elif 'vazio' in var_strErro:
                    var_dictContagemErros['dados_vazios'] += 1
                else:
                    var_dictContagemErros['outros'] += 1
                    logger.error(f"Erro ao processar AppID {var_dictDadosRaw.get('appid', 'DESCONHECIDO')}: {e}")
            except Exception as e:
                var_intErrosTransformacao += 1
                var_dictContagemErros['outros'] += 1
                logger.error(f"Erro inesperado ao processar AppID {var_dictDadosRaw.get('appid', 'DESCONHECIDO')}: {e}")
        
        logger.info(f"{len(var_listDadosUnificados)} jogos transformados com sucesso")
        
        if var_intErrosTransformacao > 0:
            logger.warning(f"{var_intErrosTransformacao} erros de transformação:")
            logger.warning(f"  - Detalhes ausentes: {var_dictContagemErros['detalhes_ausentes']}")
            logger.warning(f"  - AppID inválido: {var_dictContagemErros['appid_invalido']}")
            logger.warning(f"  - Dados vazios: {var_dictContagemErros['dados_vazios']}")
            logger.warning(f"  - Outros erros: {var_dictContagemErros['outros']}")
        
        # Inserir em steam_unificado
        if var_listDadosUnificados:
            try:
                PostgreSQLSteam.inserir_steam_unificado_batch(var_listDadosUnificados)
                
            except Exception as e:
                logger.error(f"Erro ao inserir em steam_unificado: {e}")
        else:
            logger.warning("Nenhum jogo válido para inserir em steam_unificado")