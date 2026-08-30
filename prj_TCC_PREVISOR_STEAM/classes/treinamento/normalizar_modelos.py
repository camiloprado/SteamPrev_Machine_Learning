from prj_TCC_PREVISOR_STEAM.classes.data.repositories.postgre_bdgeral import PostgreSQLBDGeral
from sklearn.model_selection import train_test_split, GroupShuffleSplit

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

import logging

logger = logging.getLogger("treino.normalizar")

class NormalizarModelos:
    """
    Classe para normalizar os dados utilizados nos modelos
    """

    _var_dfDadosTreinamento = None
    _var_dfAmostrasTemporais = None
    _var_dictSplits = None

    # Janela histórica em anos (ML_JANELA_ANOS, padrão 5).
    _var_intAnosJanelaHistorico: int = int(os.getenv("ML_JANELA_ANOS", "5"))
    _var_boolJanelaExtendida: bool = str(os.getenv("ML_JANELA_EXTENDIDA", "False")).lower() in ("true", "1", "yes")

    _var_floatThresholdDirecao = 0.03
    _var_listHorizontes = ["30d", "60d", "90d"]
    _var_dictMapHorizonteColuna = {
        "30d": "alvo_direcao_30d",
        "60d": "alvo_direcao_60d",
        "90d": "alvo_direcao_90d",
    }

    # Calendário de liquidações Steam: por padrão dias fixos (Spring/Summer/Autumn/Winter),
    # substituído por um calendário derivado dos próprios dados (ver
    # _calcular_calendario_promocoes_empirico) quando ML_CALENDARIO_PROMOCOES_EMPIRICO=True.
    _var_listDiasGrandesPromocoesPadrao = [75, 177, 327, 355]
    _var_dictCalendarioPromocoesPorAno: dict[int, list[int]] = {}
    _var_listDiasCanonicosPromocoes: list[int] = list(_var_listDiasGrandesPromocoesPadrao)

    @classmethod
    def obter_horizontes_disponiveis(cls) -> list[str]:
        """Retorna a lista de horizontes configurados para classificação."""
        return list(cls._var_listHorizontes)

    @classmethod
    def obter_estrategia_split_ativa(cls) -> str:
        """Retorna a estratégia de split usada no treino atual ("grupo" ou "walkforward")."""
        if cls._var_dictSplits is None:
            cls._preparar_todos_splits()
        return cls._var_dictSplits.get("estrategia_split", "grupo")

    @classmethod
    def _remover_outliers_iqr(cls, arg_dfDados: pd.DataFrame, arg_serMaskTreino: pd.Series, arg_listColunas: list[str], arg_floatFator: float = 1.5) -> pd.Series:
        """
        Marca outliers via IQR (limites calculados só nas linhas de treino, para não vazar
        informação do teste) nas colunas informadas. Mesmos limites aplicados a treino e teste.

        Retorna:
        - pd.Series[bool]: True para linhas dentro dos limites (a manter), indexada como arg_dfDados.
        """
        var_serManter = pd.Series(True, index=arg_dfDados.index)
        for var_strCol in arg_listColunas:
            if var_strCol not in arg_dfDados.columns:
                continue

            var_serTreino = pd.to_numeric(arg_dfDados.loc[arg_serMaskTreino, var_strCol], errors="coerce").dropna()
            if var_serTreino.empty:
                continue

            var_floatQ1, var_floatQ3 = var_serTreino.quantile([0.25, 0.75])
            var_floatIQR = var_floatQ3 - var_floatQ1
            if not np.isfinite(var_floatIQR) or var_floatIQR <= 0:
                continue

            var_floatLimInf = var_floatQ1 - arg_floatFator * var_floatIQR
            var_floatLimSup = var_floatQ3 + arg_floatFator * var_floatIQR
            var_serColuna = pd.to_numeric(arg_dfDados[var_strCol], errors="coerce")
            var_serDentro = var_serColuna.between(var_floatLimInf, var_floatLimSup)

            logger.info(
                f"Outliers IQR ({var_strCol}): limites=[{var_floatLimInf:.2f}, {var_floatLimSup:.2f}] | "
                f"removidos={int((~var_serDentro).sum()):,}"
            )
            var_serManter &= var_serDentro.fillna(False)

        return var_serManter

    @classmethod
    def _calcular_calendario_promocoes_empirico(cls) -> None:
        """
        Deriva o calendário real de liquidações Steam a partir dos dados coletados, em vez
        de assumir dias fixos do ano (que não se sustentam: a liquidação de Outono variou
        de dia 279 a 319 entre 2022 e 2025, quase um mês de diferença).

        Conta, por dia, quantos jogos têm desconto ativo simultaneamente; para cada ano com
        cobertura suficiente (observado até pelo menos o dia 330 e picos com magnitude
        mínima, para descartar anos com coleta parcial/esparsa), acha os 4 maiores picos
        (Spring/Summer/Autumn/Winter) via busca gulosa com exclusão de vizinhança de 30 dias.

        Preenche cls._var_dictCalendarioPromocoesPorAno (ano -> [4 dias do ano]) e
        cls._var_listDiasCanonicosPromocoes (mediana dos anos confiáveis, usada como
        fallback para anos sem dado confiável).
        """
        if cls._var_dfDadosTreinamento is None:
            cls.carregar_dados_treinamento()

        var_dictContagemPorDia: dict = {}
        for _, var_dictRow in cls._var_dfDadosTreinamento.iterrows():
            var_listHistorico = cls._separar_historico(var_dictRow.get("historico_preco"))
            for var_dictPonto in var_listHistorico:
                if var_dictPonto.get("desconto", 0.0) > 0.0:
                    var_dtDia = datetime.fromtimestamp(var_dictPonto["timestamp"]).date()
                    var_dictContagemPorDia[var_dtDia] = var_dictContagemPorDia.get(var_dtDia, 0) + 1

        if not var_dictContagemPorDia:
            logger.warning("Calendário de promoções: nenhum dia com desconto encontrado, mantendo dias fixos padrão.")
            return

        var_serContagem = pd.Series(var_dictContagemPorDia).sort_index()
        var_serContagem.index = pd.to_datetime(var_serContagem.index)
        var_serCompleta = var_serContagem.asfreq("D", fill_value=0)
        var_serSuavizada = var_serCompleta.rolling(14, min_periods=1, center=True).mean()

        var_dictCalendario = {}
        for var_intAno in sorted(set(var_serSuavizada.index.year)):
            var_serAno = var_serSuavizada[var_serSuavizada.index.year == var_intAno]
            var_intMaxDiaAno = var_serAno.index.max().timetuple().tm_yday
            if var_intMaxDiaAno < 330:
                continue  # ano com coleta incompleta (não chegou até o Outono/Inverno)

            var_serRestante = var_serAno.copy()
            var_listPicos = []
            for _ in range(4):
                if var_serRestante.empty:
                    break
                var_dtPico = var_serRestante.idxmax()
                var_listPicos.append((var_dtPico, float(var_serRestante.max())))
                var_serRestante = var_serRestante[
                    (var_serRestante.index < var_dtPico - timedelta(days=30))
                    | (var_serRestante.index > var_dtPico + timedelta(days=30))
                ]

            if len(var_listPicos) < 4 or min(v for _, v in var_listPicos) < 300:
                continue  # ano com dados esparsos/pouco confiáveis (ex.: início da coleta)

            var_listPicos.sort(key=lambda item: item[0])
            var_dictCalendario[var_intAno] = [dt.timetuple().tm_yday for dt, _ in var_listPicos]

        cls._var_dictCalendarioPromocoesPorAno = var_dictCalendario

        if var_dictCalendario:
            var_arrSlots = np.array(list(var_dictCalendario.values()))
            cls._var_listDiasCanonicosPromocoes = [int(round(v)) for v in np.median(var_arrSlots, axis=0)]
            logger.info(f"Calendário de promoções derivado dos dados: {var_dictCalendario}")
            logger.info(f"Dias canônicos (mediana, fallback): {cls._var_listDiasCanonicosPromocoes}")
        else:
            logger.warning("Calendário de promoções: nenhum ano com dados confiáveis, mantendo dias fixos padrão.")

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

        var_intQtdExemplos = len(arg_dfAmostras)
        logger.info(f"Quantidade de exemplos: {var_intQtdExemplos:,}")
        logger.info("Tipo de Classe: Discreta (cai / mantem / sobe)")

        for var_strHorizonte, var_strColuna in cls._var_dictMapHorizonteColuna.items():
            if var_strColuna not in arg_dfAmostras.columns:
                continue
            var_serDistribuicao = arg_dfAmostras[var_strColuna].value_counts(dropna=False)
            logger.info(f"Distribuição de classe ({var_strHorizonte}): {var_serDistribuicao.to_dict()}")
            if not var_serDistribuicao.empty:
                var_floatErroMajoritario = 1.0 - (float(var_serDistribuicao.max()) / float(var_intQtdExemplos))
                logger.info(
                    f"  Majoritária: {var_serDistribuicao.idxmax()} ({int(var_serDistribuicao.max()):,}) | "
                    f"Minoritária: {var_serDistribuicao.idxmin()} ({int(var_serDistribuicao.min()):,}) | "
                    f"Erro majoritário: {var_floatErroMajoritario:.4f}"
                )

        if "alvo_direcao_preco" in arg_dfAmostras.columns:
            var_serProxEvento = arg_dfAmostras["alvo_direcao_preco"].value_counts(dropna=False)
            logger.info(
                f"Distribuição próximo evento (não é o alvo dos classificadores 30/60/90d): "
                f"{var_serProxEvento.to_dict()}"
            )

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

            # Tentativa extra de extrair o preço de campos alternativos.
            if var_floatPreco is None:
                var_floatPreco = var_dictItem.get("price")
            
            # Se o preço ainda estiver ausente, tenta o campo "new" (valor atual em desconto).
            if var_floatPreco is None:
                var_floatPreco = var_dictItem.get("new")

            try:
                # Converte timestamp para epoch e preço para float, com validação.
                var_intTimestamp = NormalizarModelos._converter_timestamp_para_epoch(var_strTimestamp)
                if var_intTimestamp is None:
                    continue
                var_floatPreco = float(var_floatPreco)
            except (TypeError, ValueError):
                continue

            # Se o timestamp ou preço forem inválidos (não numéricos ou negativos), ignora este ponto do histórico.
            if var_intTimestamp <= 0 or var_floatPreco <= 0:
                continue

            # Extrai o desconto como float numérico válido.
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
    def _extrair_alvos_horizonte(cls, arg_intTimestampAtual: int, arg_floatPrecoAtual: float, arg_listHistorico: list, arg_intIdx: int, arg_listDiasHorizonte: list, arg_intUltimoTimestampJogo: int, arg_floatThreshold: float) -> dict:
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
        - arg_intUltimoTimestampJogo (int): Timestamp do último ponto coletado
          para ESTE jogo (não o máximo global do dataset — um jogo com coleta
          mais esparsa/antiga não deve ser rotulado "mantém" só porque outro
          jogo tem dados mais recentes).
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
                if (arg_intUltimoTimestampJogo - arg_intTimestampAtual) >= (var_intDiasH * 86400):
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
        O campo de dias é limitado a REGRESSAO_MAX_DIAS (padrão 90 dias) para evitar distorção por outliers.

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
                var_intMaxDias = int(os.getenv("REGRESSAO_MAX_DIAS", 90))
                var_intDiasProxDesconto = min(var_intDiasBruto, var_intMaxDias)
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

        # Calendário empírico (por ano) quando disponível; cai para a mediana canônica
        # dos anos confiáveis quando o ano da amostra não tem dado suficiente.
        var_listDiasEsteAno = cls._var_dictCalendarioPromocoesPorAno.get(
            var_dtAtual.year, cls._var_listDiasCanonicosPromocoes
        )
        var_listDiasProxAno = cls._var_dictCalendarioPromocoesPorAno.get(
            var_dtAtual.year + 1, cls._var_listDiasCanonicosPromocoes
        )

        var_intDiasProxPromo = 999
        for var_intDiaPromo in var_listDiasEsteAno:
            if var_intDiaPromo >= var_intDiaDoAno:
                var_intDiasProxPromo = min(var_intDiasProxPromo, var_intDiaPromo - var_intDiaDoAno)

        if var_intDiasProxPromo == 999:
            var_intDiasProxPromo = (365 - var_intDiaDoAno) + min(var_listDiasProxAno)
            
        var_listPrecosJanela = [var_dictItem["preco"] for var_dictItem in arg_listJanela]
        var_listDescontosJanela = [var_dictItem.get("desconto", 0.0) for var_dictItem in arg_listJanela]
        var_listTimestampsJanela = [var_dictItem["timestamp"] for var_dictItem in arg_listJanela]

        var_intDiasDesdeUltimoDesconto = 9999
        for var_intK in range(len(arg_listJanela) - 1, -1, -1):
            if arg_listJanela[var_intK].get("desconto", 0.0) > 0.0:
                var_intDiasDesdeUltimoDesconto = int((arg_intTimestampAtual - arg_listJanela[var_intK]["timestamp"]) / 86400)
                break
                
        # Janela efetiva: dobra quando ML_JANELA_EXTENDIDA=True (captura ciclos históricos mais longos).
        var_intAnosEfetivos = cls._var_intAnosJanelaHistorico * 2 if cls._var_boolJanelaExtendida else cls._var_intAnosJanelaHistorico
        var_intSegundosJanelaNoPreco = var_intAnosEfetivos * 365 * 86400
        var_intTimestampLimiteNoPreco = arg_intTimestampAtual - var_intSegundosJanelaNoPreco
        var_intDiasNoPrecoAtual = 0
        for var_intK in range(arg_intIdx - 1, -1, -1):
            var_dictPontoK = arg_listHistorico[var_intK]
            # Para ao atingir o limite da janela configurada
            if var_dictPontoK["timestamp"] < var_intTimestampLimiteNoPreco:
                break
            var_floatPrecoPonto = var_dictPontoK["preco"]
            if var_floatPrecoPonto > 0 and abs(var_floatPrecoPonto - arg_floatPrecoAtual) / arg_floatPrecoAtual < 0.01:
                var_intDiasNoPrecoAtual = int((arg_intTimestampAtual - var_dictPontoK["timestamp"]) / 86400)
            else:
                break
                
        var_intTotalDescontosJanela = sum(1 for var_intDesconto in var_listDescontosJanela if var_intDesconto > 0)
        var_intDiasJanela = max(1, int((var_listTimestampsJanela[-1] - var_listTimestampsJanela[0]) / 86400))
        var_floatFreqDescontosAno = (var_intTotalDescontosJanela / var_intDiasJanela) * 365 if var_intDiasJanela > 0 else 0.0
        
        var_floatPrecoMinJanela = float(np.min(var_listPrecosJanela))
        var_floatRatioPrecoVsMin = arg_floatPrecoAtual / var_floatPrecoMinJanela if var_floatPrecoMinJanela > 0 else 1.0

        # Quão atípico o preço atual é frente à própria janela do jogo (escala relativa,
        # não sofre com o drift de preço absoluto do catálogo ao longo do tempo).
        var_floatMediaJanela = float(np.mean(var_listPrecosJanela))
        var_floatStdJanela = float(np.std(var_listPrecosJanela))
        var_floatZscorePreco = (arg_floatPrecoAtual - var_floatMediaJanela) / var_floatStdJanela if var_floatStdJanela > 0 else 0.0

        return {
            "preco_media_janela": var_floatMediaJanela,
            "preco_std_janela": var_floatStdJanela,
            "preco_zscore_janela": var_floatZscorePreco,
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

        cls._calcular_calendario_promocoes_empirico()

        var_listAmostras = []
        var_intAnosJanela = cls._var_intAnosJanelaHistorico
        var_intSegundosJanela = var_intAnosJanela * 365 * 86400
        var_floatThreshold = cls._var_floatThresholdDirecao
        var_listDiasHorizonte = [30, 60, 90]
        var_intAmostrasDescartadas = 0
        var_intAmostrasGeradas = 0
        var_intTotalJogos = len(cls._var_dfDadosTreinamento)
        var_setMarcosLogados = set()
        logger.info(f"Progresso: 0% — 0/{var_intTotalJogos:,} jogos")

        for var_intIdxJogo, (_, var_dictRow) in enumerate(cls._var_dfDadosTreinamento.iterrows(), start=1):
            var_listHistorico = cls._separar_historico(var_dictRow.get("historico_preco"))
            if len(var_listHistorico) >= 2:
                var_floatReviewScore = pd.to_numeric(var_dictRow.get("review_score"), errors="coerce")
                var_intUltimoTimestampJogo = var_listHistorico[-1]["timestamp"]

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
                    var_dictAlvosHorizonte = cls._extrair_alvos_horizonte(var_intTimestampAtual, var_floatPrecoAtual, var_listHistorico, var_intIdx, var_listDiasHorizonte, var_intUltimoTimestampJogo, var_floatThreshold)
                    var_intDiasProxDesconto, var_floatDescontoEsperado = cls._extrair_alvos_regressao(var_intTimestampAtual, var_listHistorico, var_intIdx)
                    var_dictFeatures = cls._extrair_features(var_intTimestampAtual, var_floatPrecoAtual, var_listJanela, var_listHistorico, var_intIdx)

                    var_dictAmostra = {
                        "appid": var_dictRow.get("appid"),
                        "timestamp_atual": var_intTimestampAtual,  # p/ split temporal (walk-forward)
                        "review_score": float(var_floatReviewScore) if pd.notna(var_floatReviewScore) else 0.0,
                        "preco_catalogo": var_floatPrecoAtual,
                        **var_dictFeatures,
                        "alvo_direcao_preco": var_strDirecaoProxEvento,
                        "alvo_dias_ate_desconto": var_intDiasProxDesconto,
                        "alvo_desconto_esperado": var_floatDescontoEsperado,
                        **var_dictAlvosHorizonte,
                    }
                    var_listAmostras.append(var_dictAmostra)
                    var_intAmostrasGeradas += 1

            var_floatFrac = var_intIdxJogo / max(var_intTotalJogos, 1)
            for var_floatMarco, var_strPct in ((0.25, "25%"), (0.5, "50%"), (0.75, "75%"), (1.0, "100%")):
                if var_strPct not in var_setMarcosLogados and var_floatFrac >= var_floatMarco:
                    var_setMarcosLogados.add(var_strPct)
                    logger.info(
                        f"Progresso construção amostras temporais: {var_strPct} — "
                        f"{var_intIdxJogo:,}/{var_intTotalJogos:,} jogos, {var_intAmostrasGeradas:,} amostras"
                    )

        cls._var_dfAmostrasTemporais = pd.DataFrame(var_listAmostras)
        if cls._var_dfAmostrasTemporais.empty:
            raise ValueError("Nenhuma amostra temporal foi gerada a partir de historico_preco.")

        logger.info(f"Amostras temporais criadas (origem em preço cheio): {var_intAmostrasGeradas:,}")
        logger.info(f"Pontos ignorados por já estarem em promoção: {var_intAmostrasDescartadas:,}")

        for var_strHorizonte, var_strColuna in cls._var_dictMapHorizonteColuna.items():
            if var_strColuna in cls._var_dfAmostrasTemporais.columns:
                var_serDist = cls._var_dfAmostrasTemporais[var_strColuna].value_counts(dropna=False)
                logger.info(f"Distribuição alvo ({var_strHorizonte}): {var_serDist.to_dict()}")

        return cls._var_dfAmostrasTemporais

    @classmethod
    def _split_grupo_appid(cls, arg_dfDataframeCopy: pd.DataFrame, arg_listFeatures: list[str]) -> tuple[pd.Series, pd.Series]:
        """
        Split por appid (GroupShuffleSplit, 20% teste) — nenhum jogo aparece em treino
        e teste ao mesmo tempo. Não é temporal: o modelo pode ver todos os períodos do
        calendário via outros jogos, o que tende a inflar as métricas (ver comparativo
        com `_split_walkforward`).

        Retorna:
        - tuple[pd.Series, pd.Series]: máscaras booleanas (treino, teste), indexadas como arg_dfDataframeCopy.
        """
        var_dictMapRotulo = {"cai": 0, "mantem": 1, "sobe": 2}
        var_serGroups = arg_dfDataframeCopy["appid"]

        try:
            var_dfXBase = arg_dfDataframeCopy[arg_listFeatures].fillna(0.0)
            var_serYBase = arg_dfDataframeCopy["alvo_direcao_preco"].map(var_dictMapRotulo)

            var_objGSplit = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
            var_arrTrainIdx, var_arrTestIdx = next(var_objGSplit.split(var_dfXBase, var_serYBase, groups=var_serGroups))

            var_setTrainAppids = set(var_serGroups.iloc[var_arrTrainIdx].unique())
            var_setTestAppids = set(var_serGroups.iloc[var_arrTestIdx].unique())

            logger.info(f"Split por appid: apps únicos totais={var_serGroups.nunique():,}")
            logger.info(f"Apps treino: {len(var_setTrainAppids):,} | Apps teste: {len(var_setTestAppids):,}")

        except Exception as e:
            logger.warning(f"Fallback para split aleatório (sem GroupShuffleSplit): {e}")
            var_serYBase = arg_dfDataframeCopy["alvo_direcao_preco"].map(var_dictMapRotulo)

            var_arrTrainIdx, var_arrTestIdx = train_test_split(
                range(len(arg_dfDataframeCopy)),
                test_size=0.2,
                random_state=42,
                stratify=var_serYBase,
            )
            var_setTrainAppids = set(var_serGroups.iloc[var_arrTrainIdx].unique())
            var_setTestAppids = set(var_serGroups.iloc[var_arrTestIdx].unique())

        return var_serGroups.isin(var_setTrainAppids), var_serGroups.isin(var_setTestAppids)

    @classmethod
    def _split_walkforward(cls, arg_dfDataframeCopy: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        """
        Split temporal: treino = passado, teste = futuro (corte por `timestamp_atual`).
        Simula o cenário real de uso (prever o futuro nunca visto) — não deixa o modelo
        ver a sazonalidade do período de teste através de outros jogos, ao contrário do
        split por appid.

        Tamanho do teste configurável via ML_WALKFORWARD_TEST_SIZE (padrão 0.2), ou, se
        ML_WALKFORWARD_JANELA_DIAS estiver definida, o teste passa a ser uma janela curta
        e fixa (últimos N dias) em vez de uma fração do dataset — reflete a cadência real
        de re-treino do sistema em produção (o modelo nunca fica "velho" por muito tempo),
        em vez do gap de ~10 meses que a fração de 20% acaba gerando neste dataset.

        Retorna:
        - tuple[pd.Series, pd.Series]: máscaras booleanas (treino, teste), indexadas como arg_dfDataframeCopy.
        """
        var_strJanelaDias = os.getenv("ML_WALKFORWARD_JANELA_DIAS")
        var_intTimestampMax = int(arg_dfDataframeCopy["timestamp_atual"].max())

        if var_strJanelaDias:
            var_intJanelaDias = int(var_strJanelaDias)
            var_intTsCorte = var_intTimestampMax - (var_intJanelaDias * 86400)
        else:
            var_floatTestSize = float(os.getenv("ML_WALKFORWARD_TEST_SIZE", "0.2"))
            var_serOrdenado = arg_dfDataframeCopy["timestamp_atual"].sort_values()
            var_intCorte = int(len(var_serOrdenado) * (1 - var_floatTestSize))
            var_intTsCorte = int(var_serOrdenado.iloc[var_intCorte])

        var_serMaskTreino = arg_dfDataframeCopy["timestamp_atual"] < var_intTsCorte
        var_serMaskTeste = ~var_serMaskTreino

        logger.info(
            f"Split walk-forward: corte temporal={pd.to_datetime(var_intTsCorte, unit='s').date()} | "
            f"treino={int(var_serMaskTreino.sum()):,} | teste={int(var_serMaskTeste.sum()):,}"
        )
        return var_serMaskTreino, var_serMaskTeste

    @classmethod
    def _split_grupo_temporal(cls, arg_dfDataframeCopy: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        """
        Split duplo (grupo + temporal): o teste só contém linhas de appids nunca vistos
        no treino E de um período posterior ao corte temporal — elimina simultaneamente
        os dois vetores de vazamento (jogo conhecido e sazonalidade vista via outros jogos).

        Treino = appid fora do grupo de teste E timestamp < corte.
        Teste  = appid do grupo de teste E timestamp >= corte.
        Linhas que não se encaixam em nenhuma das duas condições são descartadas.

        Tamanho do grupo de teste configurável via ML_GRUPO_TEMPORAL_TEST_SIZE (padrão 0.2).

        Retorna:
        - tuple[pd.Series, pd.Series]: máscaras booleanas (treino, teste), indexadas como arg_dfDataframeCopy.
        """
        var_floatTestSize = float(os.getenv("ML_GRUPO_TEMPORAL_TEST_SIZE", "0.2"))
        var_serOrdenado = arg_dfDataframeCopy["timestamp_atual"].sort_values()
        var_intCorte = int(len(var_serOrdenado) * (1 - var_floatTestSize))
        var_intTsCorte = int(var_serOrdenado.iloc[var_intCorte])

        var_serAppids = arg_dfDataframeCopy["appid"].unique()
        var_rng = np.random.default_rng(42)
        var_arrAppidsEmbaralhados = var_rng.permutation(var_serAppids)
        var_intCorteAppids = int(len(var_arrAppidsEmbaralhados) * (1 - var_floatTestSize))
        var_setTestAppids = set(var_arrAppidsEmbaralhados[var_intCorteAppids:])

        var_serEhAppidTeste = arg_dfDataframeCopy["appid"].isin(var_setTestAppids)
        var_serEhFuturo = arg_dfDataframeCopy["timestamp_atual"] >= var_intTsCorte

        var_serMaskTreino = ~var_serEhAppidTeste & ~var_serEhFuturo
        var_serMaskTeste = var_serEhAppidTeste & var_serEhFuturo

        logger.info(
            f"Split grupo+temporal: corte temporal={pd.to_datetime(var_intTsCorte, unit='s').date()} | "
            f"apps teste={len(var_setTestAppids):,} de {len(var_serAppids):,} | "
            f"treino={int(var_serMaskTreino.sum()):,} | teste={int(var_serMaskTeste.sum()):,} | "
            f"descartadas={int((~var_serMaskTreino & ~var_serMaskTeste).sum()):,}"
        )
        return var_serMaskTreino, var_serMaskTeste

    @classmethod
    def _preparar_todos_splits(cls) -> None:
        """
        Prepara os splits de treino/teste para todos os horizontes e para regressão.

        Faz o split (por appid ou walk-forward, conforme ML_ESTRATEGIA_SPLIT) UMA VEZ
        e reutiliza a mesma máscara treino/teste para todos os horizontes, garantindo
        consistência. A partir daqui (remoção de outliers, filtro por horizonte de
        regressão, etc.) o código é idêntico para as duas estratégias — nenhuma delas
        recebe tratamento, corte ou tolerância diferente, para manter o comparativo honesto.

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
            "preco_zscore_janela",                                                                           # Quão atípico o preço atual é vs. a própria janela do jogo (relativo, não absoluto)
            "preco_media_janela",                                                                           # Preço médio na janela histórica (ML_JANELA_ANOS, padrão 5)
            "preco_std_janela",                                                                             # Desvio padrão na janela histórica (ML_JANELA_ANOS, padrão 5)
            "preco_min_janela",                                                                             # Preço mínimo na janela histórica (ML_JANELA_ANOS, padrão 5)
            "preco_max_janela",                                                                             # Preço máximo na janela histórica (ML_JANELA_ANOS, padrão 5)
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

        # Estratégia de split, compartilhada entre todos os horizontes: "grupo" (padrão,
        # GroupShuffleSplit por appid) ou "walkforward" (corte temporal, treino=passado/
        # teste=futuro). Ambas retornam só as máscaras treino/teste — o restante do método
        # trata as duas de forma idêntica.
        var_strEstrategiaSplit = str(os.getenv("ML_ESTRATEGIA_SPLIT", "grupo")).strip().lower()
        if var_strEstrategiaSplit == "walkforward":
            var_serMaskTreino, var_serMaskTeste = cls._split_walkforward(var_dfDataframeCopy)
        elif var_strEstrategiaSplit == "grupo_temporal":
            var_serMaskTreino, var_serMaskTeste = cls._split_grupo_temporal(var_dfDataframeCopy)
        else:
            if var_strEstrategiaSplit != "grupo":
                logger.warning(f"ML_ESTRATEGIA_SPLIT='{var_strEstrategiaSplit}' desconhecida, usando 'grupo'.")
                var_strEstrategiaSplit = "grupo"
            var_serMaskTreino, var_serMaskTeste = cls._split_grupo_appid(var_dfDataframeCopy, var_listFeatures)
        logger.info(f"Estratégia de split ativa: {var_strEstrategiaSplit}")

        # REMOÇÃO DE OUTLIERS (IQR, limites calculados só no treino — sem vazamento).
        # Aplicado às features monetárias, as mais sujeitas a erro de parsing/coleta.
        var_boolRemoverOutliers = str(os.getenv("ML_REMOVER_OUTLIERS", "True")).lower() in ("true", "1", "yes")
        if var_boolRemoverOutliers:
            var_floatFatorIQR = float(os.getenv("ML_OUTLIER_IQR_FATOR", "1.5"))
            var_listColunasOutlier = [
                "preco_catalogo", "preco_media_janela", "preco_max_janela",
            ]
            var_serManterOutlier = cls._remover_outliers_iqr(
                var_dfDataframeCopy, var_serMaskTreino, var_listColunasOutlier, var_floatFatorIQR
            )
            logger.info(
                f"Outliers removidos (combinado): {int((~var_serManterOutlier).sum()):,} de "
                f"{len(var_serManterOutlier):,} amostras"
            )
        else:
            var_serManterOutlier = pd.Series(True, index=var_dfDataframeCopy.index)

        # CLASSIFICAÇÃO — SPLITS POR HORIZONTE
        var_dictHorizontes = {}

        for var_strHorizonte, var_strColunaAlvo in cls._var_dictMapHorizonteColuna.items():
            if var_strColunaAlvo not in var_dfDataframeCopy.columns:
                logger.warning(f"Coluna {var_strColunaAlvo} não encontrada. Horizonte '{var_strHorizonte}' ignorado.")
                continue

            # Filtra amostras com alvo válido para este horizonte e sem outliers.
            var_boolValido = var_dfDataframeCopy[var_strColunaAlvo].notna() & var_serManterOutlier
            var_dfValido = var_dfDataframeCopy[var_boolValido]

            if var_dfValido.empty:
                logger.warning(f"Horizonte '{var_strHorizonte}': nenhuma amostra válida.")
                continue

            # Separa treino/teste mantendo a mesma máscara da estratégia ativa
            var_boolTreinoMask = var_serMaskTreino.loc[var_dfValido.index]
            var_boolTesteMask = var_serMaskTeste.loc[var_dfValido.index]

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

        # REGRESSÃO — SPLIT (INDEPENDENTE DE HORIZONTE)
        var_boolRegValido = var_dfDataframeCopy["alvo_dias_ate_desconto"].notna() & var_serManterOutlier
        var_dfReg = var_dfDataframeCopy[var_boolRegValido]

        var_boolTreinoMaskReg = var_serMaskTreino.loc[var_dfReg.index]
        var_boolTesteMaskReg = var_serMaskTeste.loc[var_dfReg.index]

        var_dfXrTrain = var_dfReg[var_boolTreinoMaskReg][var_listFeatures].fillna(0.0)
        var_dfXrTest = var_dfReg[var_boolTesteMaskReg][var_listFeatures].fillna(0.0)
        var_serYrTrain = pd.to_numeric(var_dfReg[var_boolTreinoMaskReg]["alvo_dias_ate_desconto"], errors="coerce")
        var_serYrTest = pd.to_numeric(var_dfReg[var_boolTesteMaskReg]["alvo_dias_ate_desconto"], errors="coerce")
        var_serYrDescTrain = pd.to_numeric(var_dfReg[var_boolTreinoMaskReg]["alvo_desconto_esperado"], errors="coerce")
        var_serYrDescTest = pd.to_numeric(var_dfReg[var_boolTesteMaskReg]["alvo_desconto_esperado"], errors="coerce")

        logger.info(f"Regressão: Treino={var_dfXrTrain.shape[0]:,} amostras | Teste={var_dfXrTest.shape[0]:,} amostras")

        # REGRESSÃO — SPLITS POR HORIZONTE (30d, 60d, 90d).
        # Alvo "dias" agora é filtrado por linha (igual ao "desconto"), não só clipado no valor —
        # evita treinar com amostras cujo desconto real ocorre muito além do horizonte.
        var_dictRegressaoHorizontes = {}
        var_dictMapDiasHorizonteReg = {"30d": 30, "60d": 60, "90d": 90}

        for var_strHorizReg, var_intDiasCap in var_dictMapDiasHorizonteReg.items():
            var_boolNoHorizTrain = var_serYrTrain <= var_intDiasCap
            var_boolNoHorizTest = var_serYrTest <= var_intDiasCap

            var_dfXrTrainH = var_dfXrTrain[var_boolNoHorizTrain]
            var_dfXrTestH = var_dfXrTest[var_boolNoHorizTest]
            var_serYrTrainH = var_serYrTrain[var_boolNoHorizTrain]
            var_serYrTestH = var_serYrTest[var_boolNoHorizTest]

            var_dfXrDescTrainH = var_dfXrTrain[var_boolNoHorizTrain]
            var_dfXrDescTestH = var_dfXrTest[var_boolNoHorizTest]
            var_serYrDescTrainH = var_serYrDescTrain[var_boolNoHorizTrain]
            var_serYrDescTestH = var_serYrDescTest[var_boolNoHorizTest]

            # Fallback: dias e desconto usam a mesma máscara, então esvaziam juntos.
            if var_dfXrTrainH.empty or var_dfXrTestH.empty:
                logger.warning(
                    f"Horizonte '{var_strHorizReg}': filtro por horizonte resultou em "
                    f"conjunto vazio (treino={var_dfXrTrainH.shape[0]:,}, teste={var_dfXrTestH.shape[0]:,}). "
                    "Usando conjunto completo (com clip no alvo 'dias') como fallback."
                )
                var_dfXrTrainH, var_dfXrTestH = var_dfXrTrain, var_dfXrTest
                var_serYrTrainH = var_serYrTrain.clip(upper=var_intDiasCap)
                var_serYrTestH = var_serYrTest.clip(upper=var_intDiasCap)
                var_dfXrDescTrainH, var_dfXrDescTestH = var_dfXrTrain, var_dfXrTest
                var_serYrDescTrainH, var_serYrDescTestH = var_serYrDescTrain, var_serYrDescTest

            var_dictRegressaoHorizontes[var_strHorizReg] = {
                "Xr_train": var_dfXrTrainH,
                "Xr_test": var_dfXrTestH,
                "yr_train": var_serYrTrainH,
                "yr_test": var_serYrTestH,
                "Xr_desc_train": var_dfXrDescTrainH,
                "Xr_desc_test": var_dfXrDescTestH,
                "yr_desc_train": var_serYrDescTrainH,
                "yr_desc_test": var_serYrDescTestH,
            }

            logger.info(
                f"Regressão ({var_strHorizReg}, cap={var_intDiasCap}d, filtrado por linha): "
                f"Treino={var_dfXrTrainH.shape[0]:,} | Teste={var_dfXrTestH.shape[0]:,} | "
                f"y_train max={float(var_serYrTrainH.max()):.0f} | y_test max={float(var_serYrTestH.max()):.0f} | "
                f"desconto_treino={var_dfXrDescTrainH.shape[0]:,} | desconto_teste={var_dfXrDescTestH.shape[0]:,}"
            )

        # CACHE FINAL
        cls._var_dictSplits = {
            "estrategia_split": var_strEstrategiaSplit,
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
            # Splits de desconto: só linhas cujo desconto caiu no horizonte.
            "Xr_desc_train": var_dictRegressao.get("Xr_desc_train", var_dictRegressao["Xr_train"]),
            "Xr_desc_test": var_dictRegressao.get("Xr_desc_test", var_dictRegressao["Xr_test"]),
            "yr_desc_train": var_dictRegressao["yr_desc_train"],
            "yr_desc_test": var_dictRegressao["yr_desc_test"],
        }