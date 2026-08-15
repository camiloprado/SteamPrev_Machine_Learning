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
    _var_intAnosJanelaHistorico = 5
    _var_floatThresholdDirecao = 0.03
    _var_listHorizontes = ["30d", "60d", "90d"]
    _var_dictMapHorizonteColuna = {
        "30d": "alvo_direcao_30d",
        "60d": "alvo_direcao_60d",
        "90d": "alvo_direcao_90d",
    }

    @classmethod
    def obter_horizontes_disponiveis(cls) -> list[str]:
        """Retorna a lista de horizontes configurados para classificação."""
        return list(cls._var_listHorizontes)

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
    def _separar_historico(arg_listHistorico:list) -> list:
        """
        Separar o histórico para uma lista de pontos com timestamp, preço e desconto.

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
    def _extrair_alvo_proximo_evento(cls, arg_dictAtual: dict, arg_listHistorico: list, arg_intIdx: int, arg_floatThreshold: float) -> str:
        """
        Classifica a direção do próximo evento de preço (cai, mantém ou sobe).

        Parâmetros:
        - arg_dictAtual (dict): Ponto atual do histórico com chave "preco".
        - arg_listHistorico (list): Lista completa de pontos do histórico.
        - arg_intIdx (int): Índice do ponto atual no histórico.
        - arg_floatThreshold (float): Limiar de variação para classificar direção.

        Retorna:
        - str: "cai", "mantem" ou "sobe".
        """
        var_floatPrecoAtual = arg_dictAtual["preco"]
        var_dictFuturo = arg_listHistorico[arg_intIdx + 1]
        var_floatPrecoFuturo = var_dictFuturo["preco"]
        var_floatVariacao = (var_floatPrecoFuturo - var_floatPrecoAtual) / var_floatPrecoAtual
        
        if var_floatVariacao <= -arg_floatThreshold:
            return "cai"
        elif var_floatVariacao >= arg_floatThreshold:
            return "sobe"
        return "mantem"

    @classmethod
    def _extrair_alvos_horizonte(cls, arg_intTimestampAtual: int, arg_floatPrecoAtual: float, arg_listHistorico: list, arg_intIdx: int, arg_listDiasHorizonte: list, arg_intMaxTimestampGlobal: int, arg_floatThreshold: float) -> dict:
        """
        Gera alvos de classificação para horizontes fixos (30d, 60d, 90d).

        Para cada horizonte, verifica se haverá desconto dentro da janela futura.
        Se sim, classifica como "cai". Caso contrário, compara o preço final.

        Parâmetros:
        - arg_intTimestampAtual (int): Timestamp epoch do ponto atual.
        - arg_floatPrecoAtual (float): Preço no ponto atual.
        - arg_listHistorico (list): Lista completa de pontos do histórico.
        - arg_intIdx (int): Índice do ponto atual no histórico.
        - arg_listDiasHorizonte (list): Lista de horizontes em dias (ex: [30, 60, 90]).
        - arg_intMaxTimestampGlobal (int): Timestamp máximo global do dataset.
        - arg_floatThreshold (float): Limiar de variação para classificar direção.

        Retorna:
        - dict: Dicionário com chaves "alvo_direcao_Xd" e valores "cai"/"mantem"/"sobe"/NaN.
        """
        var_dictAlvosHorizonte = {}
        for var_intDiasH in arg_listDiasHorizonte:
            var_intTimestampHorizonte = arg_intTimestampAtual + (var_intDiasH * 86400)
            
            var_listPontosHorizonte = [
                var_dictPonto for var_dictPonto in arg_listHistorico[arg_intIdx + 1:]
                if var_dictPonto["timestamp"] <= var_intTimestampHorizonte
            ]
            
            if not var_listPontosHorizonte:
                if (arg_intMaxTimestampGlobal - arg_intTimestampAtual) >= (var_intDiasH * 86400):
                    var_dictAlvosHorizonte[f"alvo_direcao_{var_intDiasH}d"] = "mantem"
                else:
                    var_dictAlvosHorizonte[f"alvo_direcao_{var_intDiasH}d"] = np.nan
                continue
                
            var_boolTemDesconto = any(
                var_dictPonto.get("desconto", 0.0) > 0.0 for var_dictPonto in var_listPontosHorizonte
            )
            
            if var_boolTemDesconto:
                var_dictAlvosHorizonte[f"alvo_direcao_{var_intDiasH}d"] = "cai"
            else:
                var_floatPrecoFimH = var_listPontosHorizonte[-1]["preco"]
                var_floatVarH = (var_floatPrecoFimH - arg_floatPrecoAtual) / arg_floatPrecoAtual
                
                if var_floatVarH <= -arg_floatThreshold:
                    var_dictAlvosHorizonte[f"alvo_direcao_{var_intDiasH}d"] = "cai"
                elif var_floatVarH >= arg_floatThreshold:
                    var_dictAlvosHorizonte[f"alvo_direcao_{var_intDiasH}d"] = "sobe"
                else:
                    var_dictAlvosHorizonte[f"alvo_direcao_{var_intDiasH}d"] = "mantem"
                    
        return var_dictAlvosHorizonte

    @classmethod
    def _extrair_alvos_regressao(cls, arg_intTimestampAtual: int, arg_listHistorico: list, arg_intIdx: int) -> tuple:
        """
        Extrai os alvos de regressão: dias até o próximo desconto e profundidade (%) do desconto.

        Percorre os pontos futuros no histórico até encontrar o primeiro com desconto > 0.
        O campo de dias é limitado a 365.

        Parâmetros:
        - arg_intTimestampAtual (int): Timestamp epoch do ponto atual.
        - arg_listHistorico (list): Lista completa de pontos do histórico.
        - arg_intIdx (int): Índice do ponto atual no histórico.

        Retorna:
        - tuple: (dias_ate_desconto, desconto_esperado_percentual). Ambos NaN se não houver desconto futuro.
        """
        var_intDiasProxDesconto = np.nan
        var_floatDescontoEsperado = np.nan
        for var_intJ in range(arg_intIdx + 1, len(arg_listHistorico)):
            var_dictPontoFuturo = arg_listHistorico[var_intJ]
            if var_dictPontoFuturo.get("desconto", 0.0) > 0.0:
                var_intDiasBruto = int((var_dictPontoFuturo["timestamp"] - arg_intTimestampAtual) / 86400)
                var_intDiasProxDesconto = min(var_intDiasBruto, 365)
                var_floatDescontoEsperado = float(var_dictPontoFuturo.get("desconto", 0.0))
                break
        return var_intDiasProxDesconto, var_floatDescontoEsperado

    @classmethod
    def _extrair_features(cls, arg_intTimestampAtual: int, arg_floatPrecoAtual: float, arg_listJanela: list, arg_listHistorico: list, arg_intIdx: int) -> dict:
        """
        Extrai as features estatísticas e temporais a partir da janela de histórico.

        Calcula métricas como média, desvio padrão, mínimo e máximo de preços,
        frequência de descontos, dias desde o último desconto, prox. grande promoção, etc.

        Parâmetros:
        - arg_intTimestampAtual (int): Timestamp epoch do ponto atual.
        - arg_floatPrecoAtual (float): Preço no ponto atual.
        - arg_listJanela (list): Pontos do histórico dentro da janela temporal.
        - arg_listHistorico (list): Lista completa de pontos do histórico.
        - arg_intIdx (int): Índice do ponto atual no histórico.

        Retorna:
        - dict: Dicionário com todas as features calculadas.
        """
        var_dtAtual = datetime.fromtimestamp(arg_intTimestampAtual)
        var_intMesAtual = var_dtAtual.month
        var_intDiaDoAno = var_dtAtual.timetuple().tm_yday
        
        var_listDiasGrandesPromocoes = [75, 177, 327, 355]
        var_intDiasProxPromo = 999
        for var_intDiaPromo in var_listDiasGrandesPromocoes:
            if var_intDiaPromo >= var_intDiaDoAno:
                var_intDiasProxPromo = min(var_intDiasProxPromo, var_intDiaPromo - var_intDiaDoAno)
                
        if var_intDiasProxPromo == 999:
            var_intDiasProxPromo = (365 - var_intDiaDoAno) + 75
            
        var_listPrecosJanela = [var_dictItem["preco"] for var_dictItem in arg_listJanela]
        var_listDescontosJanela = [var_dictItem.get("desconto", 0.0) for var_dictItem in arg_listJanela]
        var_listTimestampsJanela = [var_dictItem["timestamp"] for var_dictItem in arg_listJanela]

        var_intDiasDesdeUltimoDesconto = 9999
        for var_intK in range(len(arg_listJanela) - 1, -1, -1):
            if arg_listJanela[var_intK].get("desconto", 0.0) > 0.0:
                var_intDiasDesdeUltimoDesconto = int((arg_intTimestampAtual - arg_listJanela[var_intK]["timestamp"]) / 86400)
                break
                
        var_intDiasNoPrecoAtual = 0
        for var_intK in range(arg_intIdx - 1, -1, -1):
            var_floatPrecoPonto = arg_listHistorico[var_intK]["preco"]
            if var_floatPrecoPonto > 0 and abs(var_floatPrecoPonto - arg_floatPrecoAtual) / arg_floatPrecoAtual < 0.01:
                var_intDiasNoPrecoAtual = int((arg_intTimestampAtual - arg_listHistorico[var_intK]["timestamp"]) / 86400)
            else:
                break
                
        var_intTotalDescontosJanela = sum(1 for var_intDesconto in var_listDescontosJanela if var_intDesconto > 0)
        var_intDiasJanela = max(1, int((var_listTimestampsJanela[-1] - var_listTimestampsJanela[0]) / 86400))
        var_floatFreqDescontosAno = (var_intTotalDescontosJanela / var_intDiasJanela) * 365 if var_intDiasJanela > 0 else 0.0
        
        var_floatPrecoMinJanela = float(np.min(var_listPrecosJanela))
        var_floatRatioPrecoVsMin = arg_floatPrecoAtual / var_floatPrecoMinJanela if var_floatPrecoMinJanela > 0 else 1.0
        
        return {
            "preco_media_janela": float(np.mean(var_listPrecosJanela)),
            "preco_std_janela": float(np.std(var_listPrecosJanela)),
            "preco_min_janela": var_floatPrecoMinJanela,
            "preco_max_janela": float(np.max(var_listPrecosJanela)),
            "frequencia_descontos_por_ano": var_floatFreqDescontosAno,
            "dias_no_preco_atual": var_intDiasNoPrecoAtual,
            "ratio_preco_atual_vs_minimo": var_floatRatioPrecoVsMin,
            "desconto_medio_janela": float(np.mean(var_listDescontosJanela)),
            "desconto_max_janela": float(np.max(var_listDescontosJanela)),
            "num_promocoes_janela": var_intTotalDescontosJanela,
            "dias_janela": var_intDiasJanela,
            "dias_desde_ultimo_desconto": var_intDiasDesdeUltimoDesconto,
            "mes_atual": var_intMesAtual,
            "dia_do_ano": var_intDiaDoAno,
            "dias_para_proxima_grande_promo": var_intDiasProxPromo,
        }

    @classmethod
    def _construir_amostras_temporais(cls) -> pd.DataFrame:
        """
        Cria amostras supervisionadas temporais para direção de preço e dias até desconto.
        """
        if cls._var_dfDadosTreinamento is None:
            cls.carregar_dados_treinamento()

        var_strMaxTimestamp = cls._var_dfDadosTreinamento["historico_preco"].apply(
            lambda x: x[-1]["timestamp"] if isinstance(x, list) and x else 0
        ).max()
        var_intMaxTimestampGlobal = cls._converter_timestamp_para_epoch(var_strMaxTimestamp)
        logger.info(f"Max Timestamp Global encontrado: {var_intMaxTimestampGlobal}")
        
        var_listAmostras = []
        var_intAnosJanela = cls._var_intAnosJanelaHistorico
        var_intSegundosJanela = var_intAnosJanela * 365 * 86400
        var_floatThreshold = cls._var_floatThresholdDirecao
        var_listDiasHorizonte = [30, 60, 90]
        var_intAmostrasDescartadas = 0
        var_intAmostrasGeradas = 0

        for _, var_dictRow in cls._var_dfDadosTreinamento.iterrows():
            var_listHistorico = cls._separar_historico(var_dictRow.get("historico_preco"))
            if len(var_listHistorico) < 2:
                continue

            var_floatReviewScore = pd.to_numeric(var_dictRow.get("review_score"), errors="coerce")
            var_floatPrecoAtualCatalogo = cls._converter_preco_para_float(var_dictRow.get("preco"))

            for var_intIdx in range(len(var_listHistorico) - 1):
                var_dictAtual = var_listHistorico[var_intIdx]
                if var_dictAtual.get("desconto", 0.0) > 0.0:
                    var_intAmostrasDescartadas += 1
                    continue

                var_intTimestampAtual = var_dictAtual["timestamp"]
                var_floatPrecoAtual = var_dictAtual["preco"]
                if var_floatPrecoAtual <= 0.0:
                    continue

                var_intTimestampLimite = var_intTimestampAtual - var_intSegundosJanela
                var_listJanela = [
                    var_dictItem for var_dictItem in var_listHistorico[:var_intIdx + 1]
                    if var_dictItem["timestamp"] >= var_intTimestampLimite
                ]

                var_strDirecaoProxEvento = cls._extrair_alvo_proximo_evento(var_dictAtual, var_listHistorico, var_intIdx, var_floatThreshold)
                var_dictAlvosHorizonte = cls._extrair_alvos_horizonte(var_intTimestampAtual, var_floatPrecoAtual, var_listHistorico, var_intIdx, var_listDiasHorizonte, var_intMaxTimestampGlobal, var_floatThreshold)
                var_intDiasProxDesconto, var_floatDescontoEsperado = cls._extrair_alvos_regressao(var_intTimestampAtual, var_listHistorico, var_intIdx)
                var_dictFeatures = cls._extrair_features(var_intTimestampAtual, var_floatPrecoAtual, var_listJanela, var_listHistorico, var_intIdx)

                var_dictAmostra = {
                    "appid": var_dictRow.get("appid"),
                    "review_score": float(var_floatReviewScore) if pd.notna(var_floatReviewScore) else 0.0,
                    "preco_catalogo": float(var_floatPrecoAtualCatalogo) if pd.notna(var_floatPrecoAtualCatalogo) else 0.0,
                    "preco_atual_hist": var_floatPrecoAtual,
                    **var_dictFeatures,
                    "alvo_direcao_preco": var_strDirecaoProxEvento,
                    "alvo_dias_ate_desconto": var_intDiasProxDesconto,
                    "alvo_desconto_esperado": var_floatDescontoEsperado,
                    **var_dictAlvosHorizonte,
                }
                var_listAmostras.append(var_dictAmostra)
                var_intAmostrasGeradas += 1

        cls._var_dfAmostrasTemporais = pd.DataFrame(var_listAmostras)
        if cls._var_dfAmostrasTemporais.empty:
            raise ValueError("Nenhuma amostra temporal foi gerada a partir de historico_preco.")

        logger.info(f"Amostras temporais criadas: {var_intAmostrasGeradas:,}")
        logger.info(f"Amostras descartadas (desconto ativo no ponto de origem): {var_intAmostrasDescartadas:,}")

        for var_strHorizonte, var_strColuna in cls._var_dictMapHorizonteColuna.items():
            if var_strColuna in cls._var_dfAmostrasTemporais.columns:
                var_serDist = cls._var_dfAmostrasTemporais[var_strColuna].value_counts(dropna=False)
                logger.info(f"Distribuição alvo ({var_strHorizonte}): {var_serDist.to_dict()}")

        return cls._var_dfAmostrasTemporais

    @classmethod
    def _preparar_todos_splits(cls) -> None:
        """
        Prepara os splits de treino/teste para todos os horizontes e para regressão.

        Faz o split por appid UMA VEZ (GroupShuffleSplit) e reutiliza a mesma
        divisão de jogos para todos os horizontes, garantindo consistência
        e evitando vazamento de dados entre treino e teste.

        Parâmetros:

        Retorna:
        - None (resultado armazenado em cls._var_dictSplits)
        """
        if cls._var_dfAmostrasTemporais is None:
            cls._construir_amostras_temporais()

        var_dfDataframeCopy = cls._var_dfAmostrasTemporais.copy()

        # Lista de features para treinamento (sem desconto_atual — sempre 0 após filtro)
        var_listFeatures = [
            "review_score",                                                                                 # Positivo/Negativo
            "preco_catalogo",                                                                               # Preço original
            "preco_atual_hist",                                                                             # Preço atual do jogo na steam
            "preco_media_janela",                                                                           # Preço médio dos ultimos 180 dias
            "preco_std_janela",                                                                             # Desvio padrão dos ultimos 180 dias
            "preco_min_janela",                                                                             # Preço mínimo dos ultimos 180 dias
            "preco_max_janela",                                                                             # Preço máximo dos ultimos 180 dias
            "frequencia_descontos_por_ano",                                                                 # Frequência de descontos por ano
            "dias_no_preco_atual",                                                                          # Dias no preço atual
            "ratio_preco_atual_vs_minimo",                                                                  # Razão entre preço atual e mínimo
            "desconto_medio_janela",                                                                        # Desconto médio na janela
            "desconto_max_janela",                                                                          # Desconto máximo na janela
            "num_promocoes_janela",                                                                         # Número de promoções na janela
            "dias_janela",                                                                                  # Dias na janela
            "dias_desde_ultimo_desconto",                                                                   # Dias desde o último desconto
            "mes_atual",                                                                                    # Mês atual
            "dia_do_ano",                                                                                   # Dia do ano
            "dias_para_proxima_grande_promo",                                                               # Dias até a próxima grande promoção
        ]

        cls._log_estatisticas_treinamento(var_dfDataframeCopy, var_listFeatures)

        var_dictMapRotulo = {"cai": 0, "mantem": 1, "sobe": 2}

        # =================================================================
        # SPLIT POR APPID — UMA VEZ PARA TODOS OS HORIZONTES
        # =================================================================
        # Usa o alvo "prox_evento" como base para o split, já que todas as
        # amostras têm este alvo válido. Depois aplica o mesmo split de
        # appids para os demais horizontes.
        var_serGroups = var_dfDataframeCopy["appid"]

        try:
            var_dfXBase = var_dfDataframeCopy[var_listFeatures].fillna(0.0)
            var_serYBase = var_dfDataframeCopy["alvo_direcao_preco"].map(var_dictMapRotulo)

            var_objGSplit = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
            var_arrTrainIdx, var_arrTestIdx = next(var_objGSplit.split(var_dfXBase, var_serYBase, groups=var_serGroups))

            var_setTrainAppids = set(var_serGroups.iloc[var_arrTrainIdx].unique())
            var_setTestAppids = set(var_serGroups.iloc[var_arrTestIdx].unique())

            logger.info(f"Split por appid: apps únicos totais={var_serGroups.nunique():,}")
            logger.info(f"Apps treino: {len(var_setTrainAppids):,} | Apps teste: {len(var_setTestAppids):,}")

        except Exception as e:
            logger.warning(f"Fallback para split aleatório (sem GroupShuffleSplit): {e}")
            var_dfXBase = var_dfDataframeCopy[var_listFeatures].fillna(0.0)
            var_serYBase = var_dfDataframeCopy["alvo_direcao_preco"].map(var_dictMapRotulo)

            var_arrTrainIdx, var_arrTestIdx = train_test_split(
                range(len(var_dfDataframeCopy)),
                test_size=0.2,
                random_state=42,
                stratify=var_serYBase,
            )
            var_setTrainAppids = set(var_serGroups.iloc[var_arrTrainIdx].unique())
            var_setTestAppids = set(var_serGroups.iloc[var_arrTestIdx].unique())

        # =================================================================
        # CLASSIFICAÇÃO — SPLITS POR HORIZONTE
        # =================================================================
        var_dictHorizontes = {}

        for var_strHorizonte, var_strColunaAlvo in cls._var_dictMapHorizonteColuna.items():
            if var_strColunaAlvo not in var_dfDataframeCopy.columns:
                logger.warning(f"Coluna {var_strColunaAlvo} não encontrada. Horizonte '{var_strHorizonte}' ignorado.")
                continue

            # Filtra amostras com alvo válido para este horizonte
            var_boolValido = var_dfDataframeCopy[var_strColunaAlvo].notna()
            var_dfValido = var_dfDataframeCopy[var_boolValido]

            if var_dfValido.empty:
                logger.warning(f"Horizonte '{var_strHorizonte}': nenhuma amostra válida.")
                continue

            # Separa treino/teste mantendo o mesmo split de appids
            var_boolTreinoMask = var_dfValido["appid"].isin(var_setTrainAppids)
            var_boolTesteMask = var_dfValido["appid"].isin(var_setTestAppids)

            var_dfXTrain = var_dfValido[var_boolTreinoMask][var_listFeatures].fillna(0.0)
            var_dfXTest = var_dfValido[var_boolTesteMask][var_listFeatures].fillna(0.0)
            var_serYTrain = var_dfValido[var_boolTreinoMask][var_strColunaAlvo].map(var_dictMapRotulo)
            var_serYTest = var_dfValido[var_boolTesteMask][var_strColunaAlvo].map(var_dictMapRotulo)

            var_dictHorizontes[var_strHorizonte] = {
                "X_train": var_dfXTrain,
                "X_test": var_dfXTest,
                "y_train": var_serYTrain,
                "y_test": var_serYTest,
            }

            logger.info(
                f"Horizonte '{var_strHorizonte}': "
                f"Treino={var_dfXTrain.shape[0]:,} amostras | Teste={var_dfXTest.shape[0]:,} amostras"
            )

            # Distribuição de classes no treino e teste para verificar representatividade
            var_dictDistTreino = var_serYTrain.value_counts().to_dict()
            var_dictDistTeste = var_serYTest.value_counts().to_dict()
            logger.info(f"  Treino: {var_dictDistTreino} | Teste: {var_dictDistTeste}")

        # =================================================================
        # REGRESSÃO — SPLIT (INDEPENDENTE DE HORIZONTE)
        # =================================================================
        var_boolRegValido = var_dfDataframeCopy["alvo_dias_ate_desconto"].notna()
        var_dfReg = var_dfDataframeCopy[var_boolRegValido]

        var_boolTreinoMaskReg = var_dfReg["appid"].isin(var_setTrainAppids)
        var_boolTesteMaskReg = var_dfReg["appid"].isin(var_setTestAppids)

        var_dfXrTrain = var_dfReg[var_boolTreinoMaskReg][var_listFeatures].fillna(0.0)
        var_dfXrTest = var_dfReg[var_boolTesteMaskReg][var_listFeatures].fillna(0.0)
        var_serYrTrain = pd.to_numeric(var_dfReg[var_boolTreinoMaskReg]["alvo_dias_ate_desconto"], errors="coerce")
        var_serYrTest = pd.to_numeric(var_dfReg[var_boolTesteMaskReg]["alvo_dias_ate_desconto"], errors="coerce")
        var_serYrDescTrain = pd.to_numeric(var_dfReg[var_boolTreinoMaskReg]["alvo_desconto_esperado"], errors="coerce")
        var_serYrDescTest = pd.to_numeric(var_dfReg[var_boolTesteMaskReg]["alvo_desconto_esperado"], errors="coerce")

        logger.info(f"Regressão: Treino={var_dfXrTrain.shape[0]:,} amostras | Teste={var_dfXrTest.shape[0]:,} amostras")

        # =================================================================
        # REGRESSÃO — SPLITS POR HORIZONTE (30d, 60d, 90d)
        # =================================================================
        # Capa o alvo de regressão no limite do horizonte.
        # Amostras com desconto além do horizonte recebem valor = cap.
        var_dictRegressaoHorizontes = {}
        var_dictMapDiasHorizonteReg = {"30d": 30, "60d": 60, "90d": 90}

        for var_strHorizReg, var_intDiasCap in var_dictMapDiasHorizonteReg.items():
            var_serYrTrainH = var_serYrTrain.clip(upper=var_intDiasCap)
            var_serYrTestH = var_serYrTest.clip(upper=var_intDiasCap)

            var_dictRegressaoHorizontes[var_strHorizReg] = {
                "Xr_train": var_dfXrTrain,
                "Xr_test": var_dfXrTest,
                "yr_train": var_serYrTrainH,
                "yr_test": var_serYrTestH,
                "yr_desc_train": var_serYrDescTrain,
                "yr_desc_test": var_serYrDescTest,
            }

            logger.info(
                f"Regressão ({var_strHorizReg}, cap={var_intDiasCap}d): "
                f"Treino={var_dfXrTrain.shape[0]:,} | Teste={var_dfXrTest.shape[0]:,} | "
                f"y_train max={float(var_serYrTrainH.max()):.0f} | y_test max={float(var_serYrTestH.max()):.0f}"
            )

        # =================================================================
        # CACHE FINAL
        # =================================================================
        cls._var_dictSplits = {
            "horizontes": var_dictHorizontes,
            "regressao": {
                "Xr_train": var_dfXrTrain,
                "Xr_test": var_dfXrTest,
                "yr_train": var_serYrTrain,
                "yr_test": var_serYrTest,
                "yr_desc_train": var_serYrDescTrain,
                "yr_desc_test": var_serYrDescTest,
            },
            "regressao_horizontes": var_dictRegressaoHorizontes,
        }

    @classmethod
    def _obter_splits(cls, arg_strHorizonte: str = "30d") -> dict:
        """
        Retorna o dicionário de splits de treino/teste para um horizonte específico.

        A interface de retorno é compatível com os métodos de treinamento existentes:
        dict com chaves X_train, X_test, y_train, y_test, Xr_train, Xr_test, yr_train, yr_test.

        Parâmetros:
        - arg_strHorizonte (str): Nome do horizonte. Opções: "30d", "60d", "90d".

        Retorna:
        - dict: Dicionário contendo os splits de treino e teste para classificação e regressão.
        """
        if cls._var_dictSplits is None:
            cls._preparar_todos_splits()

        if arg_strHorizonte not in cls._var_dictSplits["horizontes"]:
            var_listDisponiveis = list(cls._var_dictSplits["horizontes"].keys())
            raise ValueError(
                f"Horizonte '{arg_strHorizonte}' não disponível. "
                f"Horizontes disponíveis: {var_listDisponiveis}"
            )

        var_dictHorizonte = cls._var_dictSplits["horizontes"][arg_strHorizonte]

        # Usa splits de regressão específicos do horizonte se disponíveis
        if arg_strHorizonte in cls._var_dictSplits.get("regressao_horizontes", {}):
            var_dictRegressao = cls._var_dictSplits["regressao_horizontes"][arg_strHorizonte]
        else:
            var_dictRegressao = cls._var_dictSplits["regressao"]

        return {
            "X_train": var_dictHorizonte["X_train"],
            "X_test": var_dictHorizonte["X_test"],
            "y_train": var_dictHorizonte["y_train"],
            "y_test": var_dictHorizonte["y_test"],
            "Xr_train": var_dictRegressao["Xr_train"],
            "Xr_test": var_dictRegressao["Xr_test"],
            "yr_train": var_dictRegressao["yr_train"],
            "yr_test": var_dictRegressao["yr_test"],
            "yr_desc_train": var_dictRegressao["yr_desc_train"],
            "yr_desc_test": var_dictRegressao["yr_desc_test"],
        }