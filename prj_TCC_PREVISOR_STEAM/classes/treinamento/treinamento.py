from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.SQL.postgre_generico import PostgreSQL
from prj_TCC_PREVISOR_STEAM.classes.limpeza.ProcessadorLimpeza import ProcessadorLimpeza
from prj_TCC_PREVISOR_STEAM.classes.limpeza.limpeza_dados import LimpezaDados

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, mean_squared_error, f1_score, classification_report
from sklearn.model_selection import train_test_split
import os
import xgboost as xgb
import lightgbm as lgb
import pandas as pd
import numpy as np
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class TreinarModelo:
    """
    Classe para treinar modelos de Machine Learning para previsão de promoções Steam.
    
    Utiliza dados de:
    - steam_unificado: Informações estruturadas + JSONB (detalhes e reviews)
    - steam_raw: Dados brutos JSONB completos
    - itad_raw: Histórico de preços do IsThereAnyDeal
    
    Estratégia: Treinamento incremental a cada 90 dias baseado em ultima_atualizacao
    
    Algoritmos disponíveis:
    - RandomForest: Baseline (rápido, interpretável)
    - XGBoost: Alta performance, resistente a overfitting
    - LightGBM: Muito rápido, eficiente com grandes datasets
    """
    
    @classmethod
    def carregar_dados_treinamento(cls):
        """
        Carrega o pipeline completo de limpeza dos dados para treinamento do modelo.
        """

        var_objPipeline = ProcessadorLimpeza.carregar_pipeline()
        
        
    @classmethod
    def carregar_dados_steam_unificado(cls, arg_intDiasJanela: int = 90) -> pd.DataFrame:
        """
        Carrega dados processados da tabela steam_unificado com filtro de janela temporal.
        
        Parâmetros:
        - arg_intDiasJanela (int): Janela de dias para filtrar dados atualizados (padrão: 90)
        
        Retorna:
        - pd.DataFrame: Dados dos jogos com features processadas (últimos N dias)
        """
        try:
            PostgreSQL.conectar()
            logger.info(f"Carregando dados de steam_unificado (últimos {arg_intDiasJanela} dias)...")
            
            var_strSQL = f"""
                SELECT * FROM steam_unificado
                WHERE ultima_atualizacao >= NOW() - INTERVAL '{arg_intDiasJanela} days'
                ORDER BY ultima_atualizacao DESC;
            """
            
            with PostgreSQL._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL)
                var_listResultados = cursor.fetchall()
                var_listColnames = [var_strDesc[0] for var_strDesc in cursor.description]
                var_listDados = [dict(zip(var_listColnames, var_tupleRow)) for var_tupleRow in var_listResultados]
            
            if not var_listDados:
                logger.warning(f"Nenhum dado encontrado em steam_unificado (últimos {arg_intDiasJanela} dias)")
                return pd.DataFrame()
            
            var_dfDados = pd.DataFrame(var_listDados)
            logger.info(f"Carregados {len(var_dfDados):,} registros de steam_unificado")
            
            return var_dfDados
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados de steam_unificado: {e}")
            return pd.DataFrame()
    
    @classmethod
    def carregar_dados_steam_raw(cls, arg_listAppids: list = None) -> pd.DataFrame:
        """
        Carrega dados brutos da tabela steam_raw.
        
        Parâmetros:
        - arg_listAppids (list): Lista de AppIDs específicos (opcional)
        
        Retorna:
        - pd.DataFrame: Dados brutos JSONB
        """
        try:
            PostgreSQL.conectar()
            logger.info("Carregando dados de steam_raw...")
            
            if arg_listAppids:
                # Carregar AppIDs específicos
                var_strSQL = f"SELECT * FROM steam_raw WHERE appid = ANY(%s);"
                with PostgreSQL._var_connConnection.cursor() as cursor:
                    cursor.execute(var_strSQL, (arg_listAppids,))
                    var_listResultados = cursor.fetchall()
                    var_listColnames = [var_strDesc[0] for var_strDesc in cursor.description]
                    var_listDados = [dict(zip(var_listColnames, var_tupleRow)) for var_tupleRow in var_listResultados]
            else:
                var_listDados = PostgreSQL.buscar_todos_dados(arg_strNomeTabela="steam_raw")
            
            if not var_listDados:
                logger.warning("Nenhum dado encontrado em steam_raw")
                return pd.DataFrame()
            
            var_dfDados = pd.DataFrame(var_listDados)
            logger.info(f"Carregados {len(var_dfDados):,} registros de steam_raw")
            
            return var_dfDados
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados de steam_raw: {e}")
            return pd.DataFrame()
    
    @classmethod
    def carregar_dados_itad_raw(cls, arg_listAppids: list = None) -> pd.DataFrame:
        """
        Carrega histórico de preços da tabela itad_raw.
        
        Parâmetros:
        - arg_listAppids (list): Lista de AppIDs específicos (opcional)
        
        Retorna:
        - pd.DataFrame: Histórico de preços com features agregadas
        """
        try:
            PostgreSQL.conectar()
            logger.info("Carregando dados de itad_raw...")
            
            if arg_listAppids:
                var_strSQL = f"SELECT * FROM itad_raw WHERE appid = ANY(%s);"
                with PostgreSQL._var_connConnection.cursor() as cursor:
                    cursor.execute(var_strSQL, (arg_listAppids,))
                    var_listResultados = cursor.fetchall()
                    var_listColnames = [var_strDesc[0] for var_strDesc in cursor.description]
                    var_listDados = [dict(zip(var_listColnames, var_tupleRow)) for var_tupleRow in var_listResultados]
            else:
                var_listDados = PostgreSQL.buscar_todos_dados(arg_strNomeTabela="itad_raw")
            
            if not var_listDados:
                logger.warning("Nenhum dado encontrado em itad_raw")
                return pd.DataFrame()
            
            var_dfDados = pd.DataFrame(var_listDados)
            logger.info(f"Carregados {len(var_dfDados):,} registros de itad_raw")
            
            # Extrai features do histórico de preços
            var_dfDados['features_historico'] = var_dfDados['dados_json'].apply(cls.extrair_features_historico_precos)
            
            # Expande features em colunas
            var_dfFeatures = pd.json_normalize(var_dfDados['features_historico'])
            var_dfDados = pd.concat([var_dfDados[['appid']], var_dfFeatures], axis=1)
            
            return var_dfDados
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados de itad_raw: {e}")
            return pd.DataFrame()
    
    @classmethod
    def extrair_features_historico_precos(cls, arg_strDados: str) -> dict:
        """
        Extrai features do histórico de preços ITAD.
        
        Parâmetros:
        - arg_strDados (str): JSON string do histórico de preços
        
        Retorna:
        - dict: Features extraídas (frequência de promoções, desconto médio, etc.)
        """
        try:
            if not arg_strDados or arg_strDados == "AUSENTE":
                return {
                    'num_promocoes': 0,
                    'desconto_medio': 0.0,
                    'desconto_maximo': 0.0,
                    'desconto_minimo': 0.0,
                    'preco_mais_baixo': 0.0,
                    'preco_mais_alto': 0.0,
                    'dias_desde_ultima_promo': 9999,
                }
            
            var_dictDados = json.loads(arg_strDados) if isinstance(arg_strDados, str) else arg_strDados
            
            # Processa histórico de preços
            var_listHistorico = var_dictDados.get('list', [])
            
            if not var_listHistorico:
                return {
                    'num_promocoes': 0,
                    'desconto_medio': 0.0,
                    'desconto_maximo': 0.0,
                    'desconto_minimo': 0.0,
                    'preco_mais_baixo': 0.0,
                    'preco_mais_alto': 0.0,
                    'dias_desde_ultima_promo': 9999,
                }
            
            # Calcula features do histórico
            var_listDescontos = [item.get('cut', 0) for item in var_listHistorico if item.get('cut', 0) > 0]
            var_listPrecos = [item.get('price_new', 0) for item in var_listHistorico if item.get('price_new', 0) > 0]
            
            # Dias desde última promoção
            var_intDiasUltimaPromo = 9999
            if var_listHistorico:
                var_intTimestamp = var_listHistorico[0].get('timestamp', 0)
                if var_intTimestamp > 0:
                    var_intDiasUltimaPromo = (datetime.now().timestamp() - var_intTimestamp) // 86400
            
            return {
                'num_promocoes': len(var_listDescontos),
                'desconto_medio': np.mean(var_listDescontos) if var_listDescontos else 0.0,
                'desconto_maximo': max(var_listDescontos) if var_listDescontos else 0.0,
                'desconto_minimo': min(var_listDescontos) if var_listDescontos else 0.0,
                'preco_mais_baixo': min(var_listPrecos) if var_listPrecos else 0.0,
                'preco_mais_alto': max(var_listPrecos) if var_listPrecos else 0.0,
                'dias_desde_ultima_promo': int(var_intDiasUltimaPromo),
            }
            
        except Exception as e:
            logger.warning(f"Erro ao extrair features de histórico de preços: {e}")
            return {
                'num_promocoes': 0,
                'desconto_medio': 0.0,
                'desconto_maximo': 0.0,
                'desconto_minimo': 0.0,
                'preco_mais_baixo': 0.0,
                'preco_mais_alto': 0.0,
                'dias_desde_ultima_promo': 9999,
            }
    
    @classmethod
    def extrair_features_detalhes(cls, arg_strDetalhes: str) -> dict:
        """
        Extrai features do campo detalhes JSONB.
        
        Parâmetros:
        - arg_strDetalhes (str): JSON string dos detalhes do jogo
        
        Retorna:
        - dict: Features extraídas
        """
        try:
            if not arg_strDetalhes or arg_strDetalhes == "AUSENTE":
                return {}
            
            var_dictDetalhes = json.loads(arg_strDetalhes) if isinstance(arg_strDetalhes, str) else arg_strDetalhes
            
            return {
                'tem_desconto': bool(var_dictDetalhes.get('price_overview', {}).get('discount_percent', 0) > 0),
                'desconto_atual': var_dictDetalhes.get('price_overview', {}).get('discount_percent', 0),
                'preco_original': var_dictDetalhes.get('price_overview', {}).get('initial', 0) / 100 if var_dictDetalhes.get('price_overview') else 0,
                'preco_final': var_dictDetalhes.get('price_overview', {}).get('final', 0) / 100 if var_dictDetalhes.get('price_overview') else 0,
                'num_conquistas': var_dictDetalhes.get('achievements', {}).get('total', 0),
                'num_dlcs': len(var_dictDetalhes.get('dlc', [])),
                'num_screenshots': len(var_dictDetalhes.get('screenshots', [])),
                'num_movies': len(var_dictDetalhes.get('movies', [])),
                'is_free': var_dictDetalhes.get('is_free', False),
                'tem_demo': 'demos' in var_dictDetalhes and len(var_dictDetalhes.get('demos', [])) > 0,
            }
            
        except Exception as e:
            logger.warning(f"Erro ao extrair features de detalhes: {e}")
            return {}
    
    @classmethod
    def preparar_dataset_completo(cls, arg_intDiasJanela: int = 90) -> pd.DataFrame:
        """
        Prepara dataset completo combinando steam_unificado, steam_raw e itad_raw com filtro temporal.
        
        Parâmetros:
        - arg_intDiasJanela (int): Janela de dias para filtrar dados atualizados (padrão: 90)
        
        Retorna:
        - pd.DataFrame: Dataset pronto para treinamento com histórico de preços
        """
        logger.info(f"Preparando dataset completo (últimos {arg_intDiasJanela} dias)...")
        
        # Carrega dados estruturados com filtro temporal
        var_dfUnificado = cls.carregar_dados_steam_unificado(arg_intDiasJanela=arg_intDiasJanela)
        
        if var_dfUnificado.empty:
            logger.error("Nenhum dado em steam_unificado. Execute o processamento ETL primeiro.")
            return pd.DataFrame()
        
        # Extrai features dos campos JSONB (detalhes_completos, reviews_completos)
        logger.info("Extraindo features dos detalhes JSONB...")
        var_dfUnificado['features_detalhes'] = var_dfUnificado['detalhes_completos'].apply(cls.extrair_features_detalhes)
        
        # Expande features extraídas em colunas
        var_dfFeatures = pd.json_normalize(var_dfUnificado['features_detalhes'])
        var_dfCompleto = pd.concat([var_dfUnificado[['appid', 'nome', 'preco', 'review_score', 'total_reviews']], var_dfFeatures], axis=1)
        
        # Carrega e integra histórico de preços ITAD
        logger.info("Carregando histórico de preços ITAD...")
        var_dfItad = cls.carregar_dados_itad_raw(arg_listAppids=var_dfUnificado['appid'].tolist())
        
        if not var_dfItad.empty:
            var_dfCompleto = var_dfCompleto.merge(var_dfItad, on='appid', how='left')
            logger.info(f"Integrado histórico de preços de {len(var_dfItad):,} jogos")
        else:
            logger.warning("Nenhum histórico de preços encontrado em itad_raw")
            # Adiciona colunas vazias para não quebrar pipeline
            var_dfCompleto['num_promocoes'] = 0
            var_dfCompleto['desconto_medio'] = 0.0
            var_dfCompleto['desconto_maximo'] = 0.0
            var_dfCompleto['preco_mais_baixo'] = 0.0
            var_dfCompleto['dias_desde_ultima_promo'] = 9999
        
        logger.info(f"Dataset preparado: {len(var_dfCompleto):,} jogos com {len(var_dfCompleto.columns)} features")
        
        return var_dfCompleto
    
    @classmethod
    def criar_features_engenharia(cls, arg_dfDados: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica feature engineering ao dataset.
        
        Parâmetros:
        - arg_dfDados (pd.DataFrame): Dataset original
        
        Retorna:
        - pd.DataFrame: Dataset com features adicionais
        """
        logger.info("Aplicando feature engineering...")
        
        var_dfDados = arg_dfDados.copy()
        
        # 1. Converte preço de string para float (formato brasileiro: R$ 1.234,56)
        def converter_preco(arg_anyX) -> float:
            try:
                if not isinstance(arg_anyX, str) or arg_anyX == 'null':
                    return 0.0
                # Remove R$ e espaços
                arg_anyX = arg_anyX.replace('R$', '').strip()
                # Separa em partes (antes e depois da vírgula)
                if ',' in arg_anyX:
                    var_listPartes = arg_anyX.split(',')
                    var_strInteiro = var_listPartes[0].replace('.', '')  # Remove pontos de milhar
                    var_strDecimal = var_listPartes[1] if len(var_listPartes) > 1 else '00'
                    return float(f"{var_strInteiro}.{var_strDecimal}")
                else:
                    # Se não tem vírgula, remove apenas os pontos
                    return float(arg_anyX.replace('.', ''))
            except:
                return 0.0
        
        var_dfDados['preco_numerico'] = var_dfDados['preco'].apply(converter_preco)
        
        # 2. Converte metacritic_score
        var_dfDados['metacritic_numerico'] = var_dfDados['metacritic_score'].apply(lambda x:
            int(x) if isinstance(x, str) and x.isdigit() else 0
        )
        
        # 3. Taxa de reviews positivas
        var_dfDados['taxa_positivas'] = var_dfDados.apply(lambda row:
            row['total_positive'] / row['total_reviews'] if row['total_reviews'] > 0 else 0,
            axis=1
        )
        
        # 4. Popularidade (total de reviews normalizado)
        var_dfDados['popularidade'] = np.log1p(var_dfDados['total_reviews'])
        
        # 5. Número de categorias e gêneros
        var_dfDados['num_categorias'] = var_dfDados['categorias'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        var_dfDados['num_generos'] = var_dfDados['genero'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        var_dfDados['num_linguagens'] = var_dfDados['linguagens'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        
        # 6. Idade do jogo (em dias desde lançamento)
        var_dfDados['dias_desde_lancamento'] = var_dfDados['data_lancamento'].apply(cls._calcular_dias_desde_lancamento)
        
        # 7. Tem desconto atual (target para classificação)
        if 'tem_desconto' not in var_dfDados.columns:
            var_dfDados['tem_desconto'] = var_dfDados['desconto_atual'] > 0
        
        logger.info(f"Features criadas. Total de colunas: {len(var_dfDados.columns)}")
        
        return var_dfDados
    
    @staticmethod
    def _calcular_dias_desde_lancamento(arg_strData: str) -> int:
        """
        Calcula dias desde o lançamento do jogo.
        
        Parâmetros:
        - arg_strData (str): Data de lançamento
        
        Retorna:
        - int: Dias desde lançamento (ou 0 se inválido)
        """
        try:
            if not arg_strData or arg_strData in ['null', 'Em Breve']:
                return 0
            
            # Tenta múltiplos formatos de data
            for var_strFormato in ['%d %b, %Y', '%d de %b de %Y', '%Y-%m-%d']:
                try:
                    var_dateData = datetime.strptime(arg_strData, var_strFormato)
                    return (datetime.now() - var_dateData).days
                except:
                    continue
            
            return 0
            
        except:
            return 0
    
    @classmethod
    def selecionar_features_treino(cls, arg_dfDados: pd.DataFrame) -> tuple:
        """
        Seleciona features numéricas para treinamento.
        
        Parâmetros:
        - arg_dfDados (pd.DataFrame): Dataset completo
        
        Retorna:
        - tuple: (X, y, feature_names)
        """
        logger.info("Selecionando features para treinamento...")
        
        # Features numéricas relevantes
        var_listFeatures = [
            'preco_numerico',
            'metacritic_numerico',
            'review_score',
            'total_reviews',
            'total_positive',
            'total_negative',
            'taxa_positivas',
            'popularidade',
            'num_categorias',
            'num_generos',
            'num_linguagens',
            'dias_desde_lancamento',
            'num_conquistas',
            'num_dlcs',
            'num_screenshots',
            'num_movies',
            # Features do histórico ITAD
            'num_promocoes',
            'desconto_medio',
            'desconto_maximo',
            'preco_mais_baixo',
            'dias_desde_ultima_promo',
        ]
        
        # Remove features que não existem no dataset
        var_listFeatures = [var_strFeatures for var_strFeatures in var_listFeatures if var_strFeatures in arg_dfDados.columns]
        
        # Remove jogos sem dados suficientes
        var_dfLimpo = arg_dfDados[var_listFeatures + ['tem_desconto']].dropna()
        
        X = var_dfLimpo[var_listFeatures]
        y = var_dfLimpo['tem_desconto']
        
        logger.info(f"Features selecionadas: {len(var_listFeatures)}")
        logger.info(f"Amostras para treino: {len(X):,}")
        logger.info(f"   - Com desconto: {y.sum():,} ({y.sum()/len(y)*100:.1f}%)")
        logger.info(f"   - Sem desconto: {(~y).sum():,} ({(~y).sum()/len(y)*100:.1f}%)")
        
        return X, y, var_listFeatures

    @classmethod
    def treinar(cls, arg_dfX, arg_arrY, arg_strTipo='classificacao', arg_floatTestSize=0.2, arg_intRandomState=42) -> tuple:
        """
        Método para iniciar o treinamento do modelo.

        Parâmetros:
        - arg_dfX (DataFrame ou array): Features
        - arg_arrY (array): Labels
        - arg_strTipo (str): 'classificacao' ou 'regressao'
        - arg_floatTestSize (float): Proporção para teste
        - arg_intRandomState (int): Semente para reprodução

        Retorna:
        - var_rfModelo: Modelo treinado
        - var_dictMetricas (dict): Métricas de avaliação
        """

        # Codifica labels se for classificação
        if arg_strTipo == 'classificacao':
            var_leLabel = LabelEncoder()
            arg_arrY = var_leLabel.fit_transform(arg_arrY)

        # Divide em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(
            arg_dfX, arg_arrY, test_size=arg_floatTestSize, random_state=arg_intRandomState
        )

        # Seleciona modelo
        if arg_strTipo == 'classificacao':
            var_rfModelo = RandomForestClassifier(random_state=arg_intRandomState)
        else:
            var_rfModelo = RandomForestRegressor(random_state=arg_intRandomState)

        # Treina
        var_rfModelo.fit(X_train, y_train)

        # Predição
        var_arrYPred = var_rfModelo.predict(X_test)

        # Métricas
        if arg_strTipo == 'classificacao':
            var_floatAccuracy = accuracy_score(y_test, var_arrYPred)
            var_floatF1 = f1_score(y_test, var_arrYPred, average='weighted')
            var_dictMetricas = {'accuracy': var_floatAccuracy, 'f1_score': var_floatF1}
        else:
            var_floatMSE = mean_squared_error(y_test, var_arrYPred)
            var_dictMetricas = {'mse': var_floatMSE}

        return var_rfModelo, var_dictMetricas
    
    @classmethod
    def treinar_xgboost(cls, arg_dfX, arg_arrY, arg_floatTestSize=0.2, arg_intRandomState=42) -> tuple:
        """
        Treina modelo XGBoost para classificação.
        
        XGBoost é conhecido por:
        - Alta performance em competições (Kaggle)
        - Resistente a overfitting
        - Lida bem com dados desbalanceados
        
        Parâmetros:
        - arg_dfX (DataFrame): Features
        - arg_arrY (array): Labels
        - arg_floatTestSize (float): Proporção para teste
        - arg_intRandomState (int): Semente para reprodução
        
        Retorna:
        - tuple: (modelo, métricas)
        """
        # Divide em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(
            arg_dfX, arg_arrY, test_size=arg_floatTestSize, random_state=arg_intRandomState, stratify=arg_arrY
        )
        
        # Calcula peso das classes para balanceamento
        var_floatScalePos = (len(y_train) - y_train.sum()) / y_train.sum()
        
        # Modelo XGBoost
        var_xgbModelo = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=var_floatScalePos,
            random_state=arg_intRandomState,
            eval_metric='logloss',
            use_label_encoder=False
        )
        
        # Treina
        var_xgbModelo.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        # Predição
        var_arrYPred = var_xgbModelo.predict(X_test)
        
        # Métricas
        var_floatAccuracy = accuracy_score(y_test, var_arrYPred)
        var_floatF1 = f1_score(y_test, var_arrYPred, average='binary')
        
        var_dictMetricas = {
            'accuracy': var_floatAccuracy,
            'f1_score': var_floatF1,
            'algoritmo': 'XGBoost'
        }
        
        return var_xgbModelo, var_dictMetricas
    
    @classmethod
    def treinar_lightgbm(cls, arg_dfX, arg_arrY, arg_floatTestSize=0.2, arg_intRandomState=42) -> tuple:
        """
        Treina modelo LightGBM para classificação.
        
        LightGBM é conhecido por:
        - Treinamento muito rápido
        - Eficiente com grandes datasets
        - Baixo uso de memória
        
        Parâmetros:
        - arg_dfX (DataFrame): Features
        - arg_arrY (array): Labels
        - arg_floatTestSize (float): Proporção para teste
        - arg_intRandomState (int): Semente para reprodução
        
        Retorna:
        - tuple: (modelo, métricas)
        """
        # Divide em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(
            arg_dfX, arg_arrY, test_size=arg_floatTestSize, random_state=arg_intRandomState, stratify=arg_arrY
        )
        
        # Calcula peso das classes
        var_floatScalePos = (len(y_train) - y_train.sum()) / y_train.sum()
        
        # Modelo LightGBM
        var_lgbModelo = lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=var_floatScalePos,
            random_state=arg_intRandomState,
            verbose=-1
        )
        
        # Treina
        var_lgbModelo.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            eval_metric='binary_logloss'
        )
        
        # Predição
        var_arrYPred = var_lgbModelo.predict(X_test)
        
        # Métricas
        var_floatAccuracy = accuracy_score(y_test, var_arrYPred)
        var_floatF1 = f1_score(y_test, var_arrYPred, average='binary')
        
        var_dictMetricas = {
            'accuracy': var_floatAccuracy,
            'f1_score': var_floatF1,
            'algoritmo': 'LightGBM'
        }
        
        return var_lgbModelo, var_dictMetricas
    
    @classmethod
    def executar_pipeline_completo(cls, arg_strAlgoritmo='todos', arg_intDiasJanela: int = 90) -> dict:
        """
        Executa pipeline completo de treinamento:
        1. Carrega dados (steam_unificado + steam_raw + itad_raw) com filtro temporal
        2. Feature engineering
        3. Seleção de features
        4. Treina modelos (RandomForest, XGBoost, LightGBM)
        5. Compara performance
        
        Parâmetros:
        - arg_strAlgoritmo (str): 'randomforest', 'xgboost', 'lightgbm' ou 'todos'
        - arg_intDiasJanela (int): Janela de dias para filtrar dados atualizados (padrão: 90)
        
        Retorna:
        - dict: Resultados de todos os modelos treinados
        """
        logger.info("="*60)
        logger.info(f"INICIANDO PIPELINE DE TREINAMENTO (Janela: {arg_intDiasJanela} dias)")
        logger.info("="*60)
        
        # 1. Preparar dataset com filtro temporal
        var_dfDados = cls.preparar_dataset_completo(arg_intDiasJanela=arg_intDiasJanela)
        
        if var_dfDados.empty:
            logger.error("Dataset vazio. Abortando treinamento.")
            return {}
        
        # 2. Feature engineering
        var_dfDados = cls.criar_features_engenharia(var_dfDados)
        
        # 3. Selecionar features
        X, y, var_listFeatures = cls.selecionar_features_treino(var_dfDados)
        
        if len(X) == 0:
            logger.error("Nenhuma amostra válida após limpeza. Abortando treinamento.")
            return {}
        
        # 4. Normalização
        logger.info("Normalizando features...")
        var_botScaler = StandardScaler()
        var_ndXScaled = var_botScaler.fit_transform(X)
        
        # 5. Treinar modelos
        var_dictResultados = {}
        
        if arg_strAlgoritmo in ['randomforest', 'todos']:
            logger.info("\n" + "="*60)
            logger.info("TREINANDO RANDOM FOREST")
            logger.info("="*60)
            var_rfModelo, var_dictMetricas = cls.treinar(
                arg_dfX=var_ndXScaled,
                arg_arrY=y,
                arg_strTipo='classificacao',
                arg_floatTestSize=0.2,
                arg_intRandomState=42
            )
            var_dictMetricas['algoritmo'] = 'RandomForest'
            var_dictResultados['randomforest'] = {
                'modelo': var_rfModelo,
                'metricas': var_dictMetricas
            }
            logger.info(f"RandomForest - Acurácia: {var_dictMetricas['accuracy']*100:.2f}% | F1: {var_dictMetricas['f1_score']:.4f}")
        
        if arg_strAlgoritmo in ['xgboost', 'todos']:
            logger.info("\n" + "="*60)
            logger.info("TREINANDO XGBOOST")
            logger.info("="*60)
            var_xgbModelo, var_dictMetricas = cls.treinar_xgboost(
                arg_dfX=var_ndXScaled,
                arg_arrY=y,
                arg_floatTestSize=0.2,
                arg_intRandomState=42
            )
            var_dictResultados['xgboost'] = {
                'modelo': var_xgbModelo,
                'metricas': var_dictMetricas
            }
            logger.info(f"XGBoost - Acurácia: {var_dictMetricas['accuracy']*100:.2f}% | F1: {var_dictMetricas['f1_score']:.4f}")
        
        if arg_strAlgoritmo in ['lightgbm', 'todos']:
            logger.info("\n" + "="*60)
            logger.info("TREINANDO LIGHTGBM")
            logger.info("="*60)
            var_lgbModelo, var_dictMetricas = cls.treinar_lightgbm(
                arg_dfX=var_ndXScaled,
                arg_arrY=y,
                arg_floatTestSize=0.2,
                arg_intRandomState=42
            )
            var_dictResultados['lightgbm'] = {
                'modelo': var_lgbModelo,
                'metricas': var_dictMetricas
            }
            logger.info(f"LightGBM - Acurácia: {var_dictMetricas['accuracy']*100:.2f}% | F1: {var_dictMetricas['f1_score']:.4f}")
        
        # 6. Comparação de resultados
        logger.info("\n" + "="*60)
        logger.info("COMPARAÇÃO DE MODELOS")
        logger.info("="*60)
        
        for var_strNomeModelo, var_dictDados in var_dictResultados.items():
            var_dictMetricas = var_dictDados['metricas']
            logger.info(f"{var_dictMetricas['algoritmo']:15s} | Acurácia: {var_dictMetricas['accuracy']*100:5.2f}% | F1-Score: {var_dictMetricas['f1_score']:.4f}")
        
        # Identifica melhor modelo
        var_strMelhorModelo = max(var_dictResultados.items(), key=lambda x: x[1]['metricas']['f1_score'])[0]
        logger.info(f"\nMELHOR MODELO: {var_dictResultados[var_strMelhorModelo]['metricas']['algoritmo']}")
        
        # 7. Feature importance do melhor modelo
        var_objMelhorModelo = var_dictResultados[var_strMelhorModelo]['modelo']
        if hasattr(var_objMelhorModelo, 'feature_importances_'):
            var_arrImportances = var_objMelhorModelo.feature_importances_
            var_listFeatureImportance = sorted(
                zip(var_listFeatures, var_arrImportances),
                key=lambda x: x[1],
                reverse=True
            )
            
            logger.info("\nTOP 10 FEATURES MAIS IMPORTANTES:")
            for i, (feature, importance) in enumerate(var_listFeatureImportance[:10], 1):
                logger.info(f"  {i}. {feature}: {importance:.4f}")
        
        return {
            'modelos': var_dictResultados,
            'melhor_modelo': var_strMelhorModelo,
            'scaler': var_botScaler,
            'features': var_listFeatures,
            'total_amostras': len(X),
            'data_treinamento': datetime.now().isoformat()
        }
    
    @classmethod
    def registrar_treinamento(cls, arg_dictResultados: dict, arg_intDiasJanela: int = 90) -> None:
        """
        Registra treinamento realizado na tabela ml_treinamento_historico.
        
        Parâmetros:
        - arg_dictResultados (dict): Resultados do pipeline de treinamento
        - arg_intDiasJanela (int): Janela de dias utilizada no treinamento
        """
        try:
            PostgreSQL.conectar()
            
            var_strMelhorModelo = arg_dictResultados['melhor_modelo']
            var_dictMetricas = arg_dictResultados['modelos'][var_strMelhorModelo]['metricas']
            
            var_strSQL = """
                INSERT INTO ml_treinamento_historico (
                    data_inicio_janela,
                    data_fim_janela,
                    total_registros_treino,
                    total_registros_validacao,
                    algoritmo,
                    acuracia,
                    f1_score,
                    parametros,
                    observacoes
                ) VALUES (
                    NOW() - INTERVAL '%s days',
                    NOW(),
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                );
            """
            
            var_jsonParametros = json.dumps({
                'features_count': len(arg_dictResultados['features']),
                'modelos_treinados': list(arg_dictResultados['modelos'].keys()),
                'melhor_modelo': var_strMelhorModelo
            })
            
            with PostgreSQL._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL, (
                    arg_intDiasJanela,
                    arg_dictResultados['total_amostras'],
                    int(arg_dictResultados['total_amostras'] * 0.2),  # 20% validação
                    var_strMelhorModelo,
                    var_dictMetricas['accuracy'],
                    var_dictMetricas['f1_score'],
                    var_jsonParametros,
                    f"Treinamento automático janela {arg_intDiasJanela} dias"
                ))
                PostgreSQL._var_connConnection.commit()
            
            logger.info(f"✅ Treinamento registrado: {var_strMelhorModelo} (Acurácia: {var_dictMetricas['accuracy']:.4f})")
            
        except Exception as e:
            logger.error(f"Erro ao registrar treinamento: {e}")
    
    @classmethod
    def verificar_ultimo_treinamento(cls) -> dict | None:
        """
        Verifica quando foi realizado o último treinamento.
        
        Retorna:
        - dict: Dados do último treinamento ou None
        """
        try:
            PostgreSQL.conectar()
            
            var_strSQL = """
                SELECT 
                    data_treinamento,
                    data_inicio_janela,
                    data_fim_janela,
                    algoritmo,
                    acuracia,
                    f1_score,
                    EXTRACT(DAY FROM NOW() - data_treinamento) as dias_desde_ultimo
                FROM ml_treinamento_historico
                ORDER BY data_treinamento DESC
                LIMIT 1;
            """
            
            with PostgreSQL._var_connConnection.cursor() as cursor:
                cursor.execute(var_strSQL)
                var_tupleResultado = cursor.fetchone()
                
                if var_tupleResultado:
                    var_listColnames = [desc[0] for desc in cursor.description]
                    return dict(zip(var_listColnames, var_tupleResultado))
                    
            return None
            
        except Exception as e:
            logger.error(f"Erro ao verificar último treinamento: {e}")
            return None
    
    @classmethod
    def executar_treinamento_incremental_90dias(cls, arg_strAlgoritmo: str = 'todos') -> dict | None:
        """
        Executa pipeline de treinamento com dados dos últimos 90 dias.
        Registra automaticamente o resultado no histórico.
        
        Parâmetros:
        - arg_strAlgoritmo (str): Algoritmo(s) a treinar ('RandomForest', 'XGBoost', 'LightGBM', 'todos')
        
        Retorna:
        - dict: Resultados do treinamento ou None em caso de erro
        """
        try:
            logger.info("="*60)
            logger.info("INICIANDO TREINAMENTO INCREMENTAL (90 DIAS)")
            logger.info("="*60)
            
            # Verificar último treinamento
            var_dictUltimo = cls.verificar_ultimo_treinamento()
            if var_dictUltimo:
                logger.info(f"Último treinamento: {var_dictUltimo['dias_desde_ultimo']:.0f} dias atrás")
                logger.info(f"  Algoritmo: {var_dictUltimo['algoritmo']}")
                logger.info(f"  Acurácia: {var_dictUltimo['acuracia']:.4f}")
            else:
                logger.info("Nenhum treinamento anterior encontrado")
            
            # Executar pipeline com janela de 90 dias
            var_dictResultados = cls.executar_pipeline_completo(
                arg_strAlgoritmo=arg_strAlgoritmo,
                arg_intDiasJanela=90
            )
            
            if var_dictResultados:
                # Registrar treinamento
                cls.registrar_treinamento(var_dictResultados, arg_intDiasJanela=90)
                logger.info("="*60)
                logger.info("TREINAMENTO INCREMENTAL CONCLUÍDO!")
                logger.info("="*60)
                return var_dictResultados
            else:
                logger.warning("Nenhum resultado obtido do treinamento")
                return None
                
        except Exception as e:
            logger.error(f"Erro no treinamento incremental: {e}")
            return None


if __name__ == "__main__":
    """
    Exemplo de uso do módulo de treinamento.
    
    Execute:
    python -m prj_TCC_PREVISOR_STEAM.classes.treinamento.treinamento
    """
    import sys
    sys.path.insert(0, '.')
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    print("\n" + "="*60)
    print("PREVISOR DE PROMOÇÕES STEAM - TREINAMENTO")
    print("="*60 + "\n")
    
    try:
        # Executar pipeline completo com todos os algoritmos
        var_dictResultados = TreinarModelo.executar_pipeline_completo(arg_strAlgoritmo='todos')
        
        if var_dictResultados:
            print("\n" + "="*60)
            print("TREINAMENTO CONCLUÍDO COM SUCESSO!")
            print("="*60)
            print(f"Total de jogos analisados: {var_dictResultados['total_amostras']:,}")
            print(f"Features utilizadas: {len(var_dictResultados['features'])}")
            print(f"\nRESULTADOS POR ALGORITMO:")
            print("-"*60)
            
            for var_strNomeModelo, var_dictDados in var_dictResultados['modelos'].items():
                var_dictMetricas = var_dictDados['metricas']
                print(f"{var_dictMetricas['algoritmo']:15s} | Acurácia: {var_dictMetricas['accuracy']*100:5.2f}% | F1: {var_dictMetricas['f1_score']:.4f}")
            
            print("-"*60)
            print(f"Melhor modelo: {var_dictResultados['modelos'][var_dictResultados['melhor_modelo']]['metricas']['algoritmo']}")
            print(f"Data: {var_dictResultados['data_treinamento']}")
            print("="*60)
        else:
            print("\nTreinamento falhou. Verifique os logs acima.")
            
    except Exception as e:
        logger.error(f"Erro durante treinamento: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        PostgreSQL.desconectar()