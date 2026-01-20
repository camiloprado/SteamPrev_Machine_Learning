from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_dados import LimpezaDados

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.compose import ColumnTransformer
import pandas as pd, logging

logger = logging.getLogger(__name__)

class ProcessadorLimpeza:
    """
    Classe responsável por processar a limpeza de dados.
    """

    @classmethod
    def processar_ITAD(cls):
        """
        Processa a limpeza dos dados da tabela itad_raw.
        
        Parâmetros:
        
        Retorna:
        - var_dfData (pd.DataFrame): DataFrame contendo os dados limpos.
        """
        var_dfDataITAD = LimpezaDados.carregar_dataframe(arg_strNomeTabela="itad_raw")
        var_dfDataITADAux = var_dfDataITAD.copy()
        var_dfDataITADAux = var_dfDataITADAux.drop_duplicates(subset=["id_itad"])
        var_dfDataITADAux = var_dfDataITADAux.drop(columns=["title", "type", "mature", "assets", "ultima_atualizacao"])
        var_dfDataITADAux = var_dfDataITADAux.reset_index(drop=True)

        return var_dfDataITADAux

    @classmethod
    def processar_itad_map(cls):
        """
        Processa a limpeza dos dados da tabela itad_map.
        
        Parâmetros:
        
        Retorna:
        - var_dfData (pd.DataFrame): DataFrame contendo os dados limpos.
        """
        var_dfDataITADMap = LimpezaDados.carregar_dataframe(arg_strNomeTabela="steam_itad_mapping")
        var_dfDataITADMapAux = var_dfDataITADMap.copy()
        var_dfDataITADMapAux = var_dfDataITADMapAux.drop_duplicates(subset=["appid"])
        var_dfDataITADMapAux = var_dfDataITADMapAux.drop_duplicates(subset=["id_itad"])
        var_dfDataITADMapAux = var_dfDataITADMapAux.drop(columns=["slug", "title", "created_at"])
        var_dfDataITADMapAux = var_dfDataITADMapAux.reset_index(drop=True)
        
        return var_dfDataITADMapAux
    
    @classmethod
    def processar_unificado(cls):
        """
        Processa a limpeza dos dados da tabela steam_unificado.
        
        Parâmetros:
        
        Retorna:
        - var_dfData (pd.DataFrame): DataFrame contendo os dados limpos.
        """
        var_listIndexReviews = ['Extremamente positivas', 'Muito positivas', 'Bem positivas', 'Positivas', 'Mistas', 'Negativas', 'Bem negativas', 'Muito negativas', 'Extremamente negativas', 'Nenhuma analise de usuario', 'Outros']

        var_dfDataUnificado = LimpezaDados.carregar_dataframe(arg_strNomeTabela="steam_unificado")
        var_dfDataUnificadoAux = var_dfDataUnificado.copy()
        var_dfDataUnificadoAux = var_dfDataUnificadoAux[var_dfDataUnificadoAux["type"] == "game"]
        var_dfDataUnificadoAux = var_dfDataUnificadoAux[var_dfDataUnificadoAux["preco"] != "Gratuito"]
        var_dfDataUnificadoAux = var_dfDataUnificadoAux.fillna({"metacritic_score": 0})
        
        # Validar e limpar a coluna de reviews
        if "review_score_desc" in var_dfDataUnificadoAux.columns:
            # Identificar valores inconsistentes
            var_boolMaskInvalidos = ~var_dfDataUnificadoAux["review_score_desc"].isin(var_listIndexReviews)
            var_intInvalidos = var_boolMaskInvalidos.sum()
            
            if var_intInvalidos > 0:
                logger.warning(f"Encontrados {var_intInvalidos} valores inconsistentes em review_score_desc")
                var_listValoresUnicosInvalidos = var_dfDataUnificadoAux.loc[var_boolMaskInvalidos, "review_score_desc"].unique()
                logger.info(f"Valores inconsistentes encontrados: {var_listValoresUnicosInvalidos}")
                
                # Substituir valores inconsistentes por 'Outros'
                var_dfDataUnificadoAux.loc[var_boolMaskInvalidos, "review_score_desc"] = "Outros"
                logger.info(f"Valores inconsistentes substituídos por 'Outros'")
            else:
                logger.info("Todos os valores de review_score_desc são válidos")
        else:
            logger.warning("Coluna 'review_score_desc' não encontrada no DataFrame")
        
        var_dfDataUnificadoAux = var_dfDataUnificadoAux.drop(columns=["ultima_atualizacao"])
        var_dfDataUnificadoAux = var_dfDataUnificadoAux.reset_index(drop=True)
        return var_dfDataUnificadoAux
    
    @classmethod
    def processar_todos(cls):
        """
        Processa a limpeza dos dados de todas as tabelas.
        
        Parâmetros:
        
        Retorna:
        - var_dfGeral (pd.DataFrame): DataFrame contendo os dados limpos combinados.
        """
        var_dfITAD = cls.processar_ITAD()
        var_dfUnificado = cls.processar_unificado()
        var_dfMapping = cls.processar_itad_map()

        logger.info("Iniciando o merge dos dados limpos...")
        logger.info(f"Número de registros em unificado: {len(var_dfUnificado)}")
        logger.info(f"Número de registros em mapping: {len(var_dfMapping)}")
        var_dfPrimeiroMerge = pd.merge(var_dfUnificado, var_dfMapping, how="left", on="appid")
        logger.info(f"Número de registros após primeiro merge: {len(var_dfPrimeiroMerge)}")

        var_dfGeral = pd.merge(var_dfPrimeiroMerge, var_dfITAD, how="left", on="appid")
        logger.info(f"Número de registros após merge: {len(var_dfGeral)}")

        return var_dfGeral

#TODO: Apagar colunas desnecessárias
#TODO: Manipular texto e atributos categóricos
#TODO: Customizar os transformadores conforme os dados
#TODO: Escalonamento das Características (MinMaxScaler, StandardScaler)
#TODO: Transformação de Pipelines