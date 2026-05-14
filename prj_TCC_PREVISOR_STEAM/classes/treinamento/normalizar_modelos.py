from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_bdgeral import PostgreSQLBDGeral
from sklearn.model_selection import train_test_split, GroupShuffleSplit

import pandas as pd
import numpy as np
from datetime import datetime

import logging

logger = logging.getLogger("treino.normalizar")

class NormalizarModelos:
    """
    Classe para normalizar os dados utilizados nos modelos
    """

    _var_dfDadosTreinamento = None
    _var_dfAmostrasTemporais = None
    _var_dictSplits = None
    _var_intJanelaHistorico = 5
    _var_floatThresholdDirecao = 0.03

    @classmethod
    def _log_estatisticas_treinamento(cls, arg_dfAmostras: pd.DataFrame, arg_listFeatures: list[str] | None = None,) -> None:
        """
        Registra estatísticas descritivas do conjunto de treino para classificação.

        Parâmetros:
        - arg_dfAmostras (pd.DataFrame): DataFrame com amostras temporais.
        - arg_listFeatures (list[str] | None): Lista de atributos a analisar.
        """
        if arg_dfAmostras is None or arg_dfAmostras.empty:
            logger.warning("Sem amostras para registrar estatísticas de treinamento.")
            return

        var_strAlvo = "alvo_direcao_preco"
        var_intQtdExemplos = len(arg_dfAmostras)
        logger.info(f"Quantidade de exemplos: {var_intQtdExemplos:,}")

        if var_strAlvo in arg_dfAmostras.columns:
            logger.info("Tipo de Classe: Discreta")

            var_serDistribuicao = arg_dfAmostras[var_strAlvo].value_counts(dropna=False)
            var_dictDistribuicao = var_serDistribuicao.to_dict()
            logger.info(f"Distribuição de Classe: {var_dictDistribuicao}")

            if not var_serDistribuicao.empty:
                var_strClasseMajoritaria = str(var_serDistribuicao.idxmax())
                var_strClasseMinoritara = str(var_serDistribuicao.idxmin())
                logger.info(f"Classe Majoritária: {var_strClasseMajoritaria} ({int(var_serDistribuicao.max()):,} exemplos)")
                logger.info(f"Classe Minoritária: {var_strClasseMinoritara} ({int(var_serDistribuicao.min()):,} exemplos)")

                # Baseline que sempre prediz a classe majoritária.
                var_floatErroMajoritario = 1.0 - (float(var_serDistribuicao.max()) / float(var_intQtdExemplos))
                logger.info(f"Erro Majoritário: {var_floatErroMajoritario:.4f}")
        else:
            logger.warning("Coluna alvo_direcao_preco não encontrada para cálculo da distribuição de classe.")

        if not arg_listFeatures:
            logger.warning("Lista de atributos vazia; não foi possível inferir tipo de atributos.")
            return

        var_intAtributosDiscretos = 0
        var_intAtributosContinuos = 0
        var_dictTipoAtributos = {}

        for var_strFeature in arg_listFeatures:
            if var_strFeature not in arg_dfAmostras.columns:
                continue

            var_serColuna = pd.to_numeric(arg_dfAmostras[var_strFeature], errors="coerce").dropna()
            if var_serColuna.empty:
                continue

            # Heurística simples: poucos valores únicos inteiros -> discreto; caso contrário -> contínuo.
            var_intUnicos = int(var_serColuna.nunique())
            var_boolInteiro = bool((var_serColuna % 1 == 0).all())
            var_boolDiscreto = var_boolInteiro and var_intUnicos <= 30

            if var_boolDiscreto:
                var_dictTipoAtributos[var_strFeature] = "Discreta"
                var_intAtributosDiscretos += 1
            else:
                var_dictTipoAtributos[var_strFeature] = "Continua"
                var_intAtributosContinuos += 1

        if var_intAtributosDiscretos > 0 and var_intAtributosContinuos > 0:
            var_strTipoAtributos = "Misto (Discreta/Continua)"
        elif var_intAtributosDiscretos > 0:
            var_strTipoAtributos = "Discreta"
        elif var_intAtributosContinuos > 0:
            var_strTipoAtributos = "Continua"
        else:
            var_strTipoAtributos = "Indeterminado"

        logger.info(f"Tipo de atributos: {var_strTipoAtributos}")
        logger.info(f"Resumo tipos de atributos: discretos={var_intAtributosDiscretos}, continuos={var_intAtributosContinuos}")
        logger.info(f"Tipos por atributo: {var_dictTipoAtributos}")
    
    @classmethod
    def carregar_dados_treinamento(cls) -> pd.DataFrame:
        """
        Método para carregar os dados de treinamento.

        Parâmetros:

        Retorna:
        - pd.DataFrame: DataFrame contendo os dados de treinamento.
        """
        logger.info("Carregando dados de treinamento...")
        var_listDados = PostgreSQLBDGeral.buscar_dados_Geral(arg_boolFiltroPadrao=True)
        cls._var_dfDadosTreinamento = pd.DataFrame(var_listDados)
        logger.info("Dados de treinamento carregados com sucesso.")
        logger.info(f"Carregados {len(var_listDados)} exemplos para treinamento.")

        if cls._var_dfDadosTreinamento.empty:
            logger.warning("Dataset de treinamento vazio após consulta da tabela steam_geral.")
        else:
            logger.info(f"Colunas disponíveis no dataset de treino: {list(cls._var_dfDadosTreinamento.columns)}")
            logger.debug("Amostra head(10) dos dados de treinamento:")
            logger.debug("\n%s", cls._var_dfDadosTreinamento.head(10).to_string(index=False))

        return cls._var_dfDadosTreinamento

    @staticmethod
    def _converter_preco_para_float(arg_strValor) -> float:
        """
        Converte string monetária no formato brasileiro para float.
        
        Parâmetros:
        - arg_strValor (str): Valor a ser convertido, pode ser string ou numérico.

        Retorna:
        - float: Valor convertido para float, ou np.nan se a conversão falhar.
        """
        if arg_strValor is None:
            return np.nan
        
        var_strValor = str(arg_strValor).strip()
        if not var_strValor:
            return np.nan

        var_strValor = var_strValor.replace("R$", "").replace(" ", "")
        var_strValor = var_strValor
        try:
            return float(var_strValor)
        except ValueError:
            return np.nan

    @staticmethod
    def _normalizar_historico(arg_listHistorico:list) -> list:
        """
        Normaliza o histórico para uma lista de pontos com timestamp, preço e desconto.

        Parâmetros:
        - arg_listHistorico: Lista de pontos com timestamp, preço e desconto.

        Retorna:
        - list: Lista de pontos normalizados.
        """
        # Validações iniciais para garantir que o histórico seja uma lista de dicionários com os campos esperados.
        if arg_listHistorico is None or (isinstance(arg_listHistorico, float) and np.isnan(arg_listHistorico)):
            return []

        # Se for uma string JSON, tenta parsear
        if isinstance(arg_listHistorico, list):
            var_listBase = arg_listHistorico
        else:
            return []

        # Normaliza cada ponto do histórico, garantindo que tenhamos timestamp, preço e desconto em formatos consistentes.
        var_listPontos = []
        for var_dictItem in var_listBase:
            if not isinstance(var_dictItem, dict):
                continue

            # Extrai timestamp, preço e desconto, aplicando validações e conversões necessárias.
            var_strTimestamp = var_dictItem.get("timestamp")
            var_dictDeal = var_dictItem.get("deal", {})
            var_dictPreco = var_dictDeal.get("price", {})
            var_floatPreco = var_dictPreco.get("amount")

            # Tentativas adicionais para extrair o preço de campos alternativos, caso o campo principal esteja ausente ou inválido.
            if var_floatPreco is None:
                var_floatPreco = var_dictItem.get("price")
            
            # Se o preço ainda estiver ausente, tenta extrair de um campo "new" dentro do dicionário do preço, que pode conter o valor atual em casos de desconto.
            if var_floatPreco is None:
                var_floatPreco = var_dictItem.get("new")

            try:
                # Converte o timestamp para epoch e o preço para float, aplicando validações para garantir que ambos sejam valores numéricos válidos.
                var_intTimestamp = NormalizarModelos._converter_timestamp_para_epoch(var_strTimestamp)
                if var_intTimestamp is None:
                    continue
                var_floatPreco = float(var_floatPreco)
            except (TypeError, ValueError):
                continue

            # Se o timestamp ou preço forem inválidos (não numéricos ou negativos), ignora este ponto do histórico.
            if var_intTimestamp <= 0 or var_floatPreco <= 0:
                continue

            # Extrai o desconto, garantindo que seja um valor numérico válido, e aplicando uma conversão para float caso seja necessário.
            var_floatDesconto = var_dictDeal.get("cut", 0)
            try:
                var_floatDesconto = float(var_floatDesconto)
            except (TypeError, ValueError):
                var_floatDesconto = 0.0

            # Adiciona o ponto normalizado à lista
            var_listPontos.append(
                {
                    "timestamp": var_intTimestamp,
                    "preco": var_floatPreco,
                    "desconto": var_floatDesconto,
                }
            )

        # Ordena os pontos por timestamp para garantir a sequência temporal correta.
        var_listPontos.sort(key=lambda item: item["timestamp"])
        return var_listPontos

    @staticmethod
    def _converter_timestamp_para_epoch(arg_strTimestamp:str) -> int | None:
        """
        Converte timestamp do histórico para epoch (segundos).

        Parâmetros:
        - arg_strTimestamp (str): Timestamp a ser convertido, pode ser string ou numérico.

        Retorna:
        - int | None: Timestamp convertido para epoch em segundos, ou None se a conversão falhar.
        """
        # Validações iniciais para garantir que o timestamp seja um valor numérico ou uma string não vazia.
        if arg_strTimestamp is None:
            return None

        var_strTimestamp = str(arg_strTimestamp).strip()
        if not var_strTimestamp:
            return None

        # Compatibilidade com sufixo UTC 'Z'
        if var_strTimestamp.endswith("Z"):
            var_strTimestamp = var_strTimestamp[:-1] + "+00:00"

        try:
            return int(datetime.fromisoformat(var_strTimestamp).timestamp())
        except ValueError:
            return None

    @classmethod
    def _construir_amostras_temporais(cls) -> pd.DataFrame:
        """
        Cria amostras supervisionadas temporais para direção de preço e dias até desconto.
        
        Parâmetros:
        
        Retorna:
        - pd.DataFrame: DataFrame com as amostras temporais criadas.
        """
        # Verifica se os dados de treinamento já foram carregados, caso contrário, carrega-os.
        if cls._var_dfDadosTreinamento is None:
            cls.carregar_dados_treinamento()

        var_listAmostras = []

        # Janela de histórico a ser considerada para criar as amostras temporais
        var_intJanela = cls._var_intJanelaHistorico

        # Threshold de variação de preço para classificar a direção como "cai", "mantem" ou "sobe"
        var_floatThreshold = cls._var_floatThresholdDirecao

        # Itera sobre cada linha do DataFrame de treinamento
        for _, var_dictRow in cls._var_dfDadosTreinamento.iterrows():
            # Normaliza o histórico de preços
            var_listHistorico = cls._normalizar_historico(var_dictRow.get("historico_preco"))

            # Verifica se o histórico tem pontos suficientes para a janela definida, caso contrário, ignora.
            if len(var_listHistorico) < (var_intJanela + 1):
                continue

            # Extrai o review score
            var_floatReviewScore = pd.to_numeric(var_dictRow.get("review_score"), errors="coerce")

            # Extrai o preço atual do catálogo
            var_floatPrecoAtualCatalogo = cls._converter_preco_para_float(var_dictRow.get("preco"))

            # Itera sobre o histórico a partir do ponto onde a janela completa pode ser formada
            for var_intIdx in range(var_intJanela, len(var_listHistorico) - 1):
                # Cria uma lista com os pontos do histórico que formam a janela
                var_listJanela = var_listHistorico[var_intIdx - var_intJanela: var_intIdx + 1]

                # Extrai o ponto atual
                var_dictAtual = var_listHistorico[var_intIdx]

                # Extrai o ponto futuro
                var_dictFuturo = var_listHistorico[var_intIdx + 1]

                # Extrai o preço atual
                var_floatPrecoAtual = var_dictAtual["preco"]

                # Extrai o preço futuro
                var_floatPrecoFuturo = var_dictFuturo["preco"]

                # Se o preço atual for zero ou negativo, ignora esta amostra
                if var_floatPrecoAtual <= 0:
                    continue

                # Calcula a variação percentual do preço entre o ponto atual e o futuro
                var_floatVariacao = (var_floatPrecoFuturo - var_floatPrecoAtual) / var_floatPrecoAtual

                # Classifica a direção do preço com base na variação e no threshold definido
                if var_floatVariacao <= -var_floatThreshold:
                    var_strDirecao = "cai"
                elif var_floatVariacao >= var_floatThreshold:
                    var_strDirecao = "sobe"
                else:
                    var_strDirecao = "mantem"

                # Calcula os dias até o próximo desconto, definindo como NaN
                var_intDiasProxDesconto = np.nan

                # Itera sobre os pontos futuros
                for var_intJ in range(var_intIdx + 1, len(var_listHistorico)):

                    # Extrai o ponto futuro
                    var_dictPontoFuturo = var_listHistorico[var_intJ]

                    # Verifica se o desconto é maior que zero
                    if var_dictPontoFuturo.get("desconto", 0) > 0:

                        # Calcula os dias até o próximo desconto com base na diferença de timestamps entre o ponto futuro e o ponto atual, convertendo de segundos para dias.
                        var_intDiasProxDesconto = int(
                            (var_dictPontoFuturo["timestamp"] - var_dictAtual["timestamp"]) / 86400 # Utiliza 86400 para converter segundos em dias
                        )
                        break
                    
                # Cria uma lista com os preços da janela
                var_listPrecosJanela = [item["preco"] for item in var_listJanela]

                # Cria uma lista com os descontos da janela
                var_listDescontosJanela = [item["desconto"] for item in var_listJanela]

                # Cria uma lista com os timestamps da janela
                var_listTimestampsJanela = [item["timestamp"] for item in var_listJanela]

                # Define 9999 como valor padrão para dias desde o último desconto
                var_intDiasDesdeUltimoDesconto = 9999

                # Itera sobre a janela de forma reversa para encontrar o último desconto.
                for var_intK in range(len(var_listJanela) - 1, -1, -1):

                    # Verifica se o desconto é maior que zero
                    if var_listJanela[var_intK]["desconto"] > 0:

                        # Se for maior que zero, calcula os dias desde o último desconto com base na diferença de timestamps entre o ponto atual e o ponto da janela onde ocorreu o desconto, convertendo de segundos para dias.
                        var_intDiasDesdeUltimoDesconto = int(
                            (var_dictAtual["timestamp"] - var_listJanela[var_intK]["timestamp"]) / 86400 # Utiliza 86400 para converter segundos em dias
                        )
                        break
                
                # Adiciona a amostra criada à lista de amostras.
                var_listAmostras.append(
                    {
                        "appid": var_dictRow.get("appid"), # Mantém o appid para referência.
                        "review_score": float(var_floatReviewScore) if pd.notna(var_floatReviewScore) else 0.0, # Extrai o review score.
                        "preco_catalogo": float(var_floatPrecoAtualCatalogo) if pd.notna(var_floatPrecoAtualCatalogo) else 0.0, # Extrai o preço atual do catálogo.
                        "preco_atual_hist": var_floatPrecoAtual, # Extrai o preço atual do histórico.
                        "preco_media_janela": float(np.mean(var_listPrecosJanela)), # Calcula a média dos preços na janela.
                        "preco_std_janela": float(np.std(var_listPrecosJanela)), # Calcula o desvio padrão dos preços na janela.
                        "preco_min_janela": float(np.min(var_listPrecosJanela)), # Calcula o mínimo dos preços na janela.
                        "preco_max_janela": float(np.max(var_listPrecosJanela)), # Calcula o máximo dos preços na janela.
                        "desconto_atual": float(var_dictAtual.get("desconto", 0.0)), # Extrai o desconto atual.
                        "desconto_medio_janela": float(np.mean(var_listDescontosJanela)), # Calcula a média dos descontos na janela.
                        "desconto_max_janela": float(np.max(var_listDescontosJanela)), # Calcula o máximo dos descontos na janela.
                        "num_promocoes_janela": int(sum(1 for d in var_listDescontosJanela if d > 0)), # Conta o número de promoções na janela.
                        "dias_janela": int((var_listTimestampsJanela[-1] - var_listTimestampsJanela[0]) / 86400), # Calcula o número de dias na janela.
                        "dias_desde_ultimo_desconto": var_intDiasDesdeUltimoDesconto, # Extrai os dias desde o último desconto.
                        "alvo_direcao_preco": var_strDirecao, # Extrai a direção do preço.
                        "alvo_dias_ate_desconto": var_intDiasProxDesconto, # Extrai os dias até o próximo desconto.
                    }
                )

        # Converte a lista de amostras para um DataFrame.
        cls._var_dfAmostrasTemporais = pd.DataFrame(var_listAmostras)

        # Verifica se foram criadas amostras temporais, caso contrário, lança um erro.
        if cls._var_dfAmostrasTemporais.empty:
            raise ValueError("Nenhuma amostra temporal foi gerada a partir de historico_preco.")

        logger.info(f"Amostras temporais criadas: {len(cls._var_dfAmostrasTemporais)}")
        logger.debug(f"Colunas das amostras temporais: {list(cls._var_dfAmostrasTemporais.columns)}")
        logger.debug("Amostra head(10) das amostras temporais:")
        logger.debug("\n%s", cls._var_dfAmostrasTemporais.head(10).to_string(index=False))
        
        return cls._var_dfAmostrasTemporais

    @classmethod
    def _obter_splits(cls) -> dict:
        """
        Prepara split único para manter comparabilidade entre modelos.
        
        Parâmetros:

        Retorna:
        - dict: Dicionário contendo os splits de treino e teste para classificação e regressão.
        """
        if cls._var_dictSplits is not None:
            return cls._var_dictSplits

        if cls._var_dfAmostrasTemporais is None:
            cls._construir_amostras_temporais()

        var_dfDataframeCopy = cls._var_dfAmostrasTemporais.copy()
        var_listFeatures = [
            "review_score",
            "preco_catalogo",
            "preco_atual_hist",
            "preco_media_janela",
            "preco_std_janela",
            "preco_min_janela",
            "preco_max_janela",
            "desconto_atual",
            "desconto_medio_janela",
            "desconto_max_janela",
            "num_promocoes_janela",
            "dias_janela",
            "dias_desde_ultimo_desconto",
        ]

        cls._log_estatisticas_treinamento(cls._var_dfAmostrasTemporais, var_listFeatures)

        var_dfX = var_dfDataframeCopy[var_listFeatures].fillna(0.0)

        var_dictMapRotulo = {"cai": 0, "mantem": 1, "sobe": 2}
        var_serYClass = var_dfDataframeCopy["alvo_direcao_preco"].map(var_dictMapRotulo)

        # Split por grupo (appid) para evitar vazamento entre amostras do mesmo jogo
        try:
            var_serGroups = var_dfDataframeCopy["appid"]
            var_objGSplit = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
            var_intTrainIndex, var_intTestIndex = next(var_objGSplit.split(var_dfX, var_serYClass, groups=var_serGroups))

            var_dfXTrain = var_dfX.iloc[var_intTrainIndex]
            var_dfXTest = var_dfX.iloc[var_intTestIndex]
            var_dfYTrain = var_serYClass.iloc[var_intTrainIndex]
            var_dfYTest = var_serYClass.iloc[var_intTestIndex]

            # Logging de verificação de leakage/representatividade
            logger.info(f"Split por appid: apps únicos totais={var_serGroups.nunique():,}")
            logger.info(f"Treino: {var_dfXTrain.shape[0]:,} amostras | Teste: {var_dfXTest.shape[0]:,} amostras")
            logger.info(
                f"Treino (apps únicos): {var_dfDataframeCopy.iloc[var_intTrainIndex]['appid'].nunique():,} | "
                f"Teste (apps únicos): {var_dfDataframeCopy.iloc[var_intTestIndex]['appid'].nunique():,}"
            )
        except Exception:
            # Fallback caso não haja coluna appid ou GroupShuffleSplit falhe
            var_dfXTrain, var_dfXTest, var_dfYTrain, var_dfYTest = train_test_split(
                var_dfX,
                var_serYClass,
                test_size=0.2,
                random_state=42,
                stratify=var_serYClass,
            )

        var_dfReg = var_dfDataframeCopy.dropna(subset=["alvo_dias_ate_desconto"]).copy()
        var_dfXReg = var_dfReg[var_listFeatures].fillna(0.0)
        var_dfYReg = pd.to_numeric(var_dfReg["alvo_dias_ate_desconto"], errors="coerce")

        # Para regressão, também evitar vazamento por appid quando possível
        try:
            var_serGroupsReg = var_dfReg["appid"]
            var_objGSplitReg = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
            var_intTrainIndexReg, var_intTestIndexReg = next(var_objGSplitReg.split(var_dfXReg, var_dfYReg, groups=var_serGroupsReg))

            var_dfXrTrain = var_dfXReg.iloc[var_intTrainIndexReg]
            var_dfXrTest = var_dfXReg.iloc[var_intTestIndexReg]
            var_dfYrTrain = var_dfYReg.iloc[var_intTrainIndexReg]
            var_dfYrTest = var_dfYReg.iloc[var_intTestIndexReg]

            logger.info(f"Regressão - Treino: {var_dfXrTrain.shape[0]:,} | Teste: {var_dfXrTest.shape[0]:,}")
            logger.info(
                f"Regressão (apps únicos) - Treino: {var_dfReg.iloc[var_intTrainIndexReg]['appid'].nunique():,} | "
                f"Teste: {var_dfReg.iloc[var_intTestIndexReg]['appid'].nunique():,}"
            )
        except Exception:
            var_dfXrTrain, var_dfXrTest, var_dfYrTrain, var_dfYrTest = train_test_split(
                var_dfXReg,
                var_dfYReg,
                test_size=0.2,
                random_state=42,
            )

        cls._var_dictSplits = {
            "X_train": var_dfXTrain,
            "X_test": var_dfXTest,
            "y_train": var_dfYTrain,
            "y_test": var_dfYTest,
            "Xr_train": var_dfXrTrain,
            "Xr_test": var_dfXrTest,
            "yr_train": var_dfYrTrain,
            "yr_test": var_dfYrTest,
        }
        return cls._var_dictSplits