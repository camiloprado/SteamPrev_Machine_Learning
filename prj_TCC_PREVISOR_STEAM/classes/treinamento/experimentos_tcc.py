"""
Este arquivo contém as implementações para o "Backlog TCC - Melhorias Futuras".
As funções aqui definidas são experimentais e podem ser habilitadas posteriormente
através do arquivo .env.

Dependências adicionais requeridas para uso completo:
pip install optuna shap fastapi uvicorn streamlit jupyter nbformat
"""

import os
import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger("treino.experimentos")

# ====================================================================================
# 1. Hyperparameter Tuning (Optuna / GridSearch para XGBoost)
# ====================================================================================
def otimizar_hiperparametros_xgboost(arg_dfX_train: pd.DataFrame, arg_serY_train: pd.Series, arg_intNumeroTreinos: int = 20) -> dict:
    """
    Otimiza os hiperparâmetros do modelo XGBoost utilizando a biblioteca Optuna.
    Habilitar com ML_EXPERIMENTAL_OPTUNA=True

    Parâmetros:
    - arg_dfX_train (pd.DataFrame): DataFrame com os dados de treinamento.
    - arg_serY_train (pd.Series): Série com os dados de treinamento.
    - arg_intNumeroTreinos (int): Número de treinos a serem realizados.

    Retorna:
    - dict: Dicionário com os melhores hiperparâmetros encontrados.
    """
    try:
        import optuna
        import xgboost as xgb
        from sklearn.metrics import f1_score
        from sklearn.model_selection import train_test_split
        
        logger.info("Iniciando otimização de hiperparâmetros com Optuna para XGBoost...")
        
        # Split interno para validação durante o Optuna
        X_tr, X_val, y_tr, y_val = train_test_split(arg_dfX_train, arg_serY_train, test_size=0.2, random_state=42)
        
        def objective(trial):
            var_dictParametros = {
                'verbosity': 0,
                'objective': 'multi:softprob',
                'num_class': 3,
                'max_depth': trial.suggest_int('max_depth', 3, 12),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'n_estimators': trial.suggest_int('n_estimators', 100, 500),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0)
            }
            
            var_objModelo = xgb.XGBClassifier(**var_dictParametros, random_state=42)
            var_objModelo.fit(X_tr, y_tr)
            var_objPreds = var_objModelo.predict(X_val)
            return f1_score(y_val, var_objPreds, average='macro')
            
        var_objStudy = optuna.create_study(direction='maximize')
        var_objStudy.optimize(objective, n_trials=arg_intNumeroTreinos)
        
        logger.info(f"Melhores hiperparâmetros encontrados: {var_objStudy.best_params}")
        return var_objStudy.best_params

    except ImportError as var_objErro:
        logger.error("Biblioteca 'optuna' ou 'xgboost' não instalada. Instale com 'pip install optuna xgboost'.")
        os.system("pip install optuna xgboost")
        return otimizar_hiperparametros_xgboost(arg_dfX_train, arg_serY_train, arg_intNumeroTreinos)
    except Exception as e:
        logger.error(f"Erro ao otimizar hiperparâmetros: {e}")
        raise e

# ====================================================================================
# 2. SHAP Values (Explicabilidade dos modelos)
# ====================================================================================
def gerar_explicabilidade_shap(arg_objModelo:object, arg_dfXTest:pd.DataFrame, arg_strNomeModelo:str="XGBoost") -> bool:
    """
    Gera gráficos de importância de features utilizando SHAP Values.
    Habilitar com ML_EXPERIMENTAL_SHAP=True
    
    Parâmetros:
        arg_objModelo (object): Objeto do modelo treinado.
        arg_dfXTest (pd.DataFrame): DataFrame com os dados de teste.
        arg_strNomeModelo (str): Nome do modelo.
    
    Retorna:
        bool: True se a explicabilidade foi gerada com sucesso, False caso contrário.
    """
    try:
        import shap
        import matplotlib.pyplot as plt
        
        logger.info(f"Gerando explicabilidade SHAP para o modelo {arg_strNomeModelo}...")
        
        # O ideal é usar uma amostra menor (ex: 5000) para calcular SHAP mais rápido
        var_dfXSample = arg_dfXTest.sample(min(5000, len(arg_dfXTest)), random_state=42) if isinstance(arg_dfXTest, pd.DataFrame) else arg_dfXTest[:5000]
        
        # Explainer Tree (funciona para XGBoost, LightGBM, RandomForest)
        var_objExplainer = shap.TreeExplainer(arg_objModelo)
        var_serSHAPValues = var_objExplainer.shap_values(var_dfXSample)
        
        # Gera o Summary Plot
        plt.figure(figsize=(10, 6))
        shap.summary_plot(var_serSHAPValues, var_dfXSample, show=False)
        
        var_strCaminhoSalvar = os.path.join("prj_TCC_PREVISOR_STEAM", "resources", "relatorios", f"shap_summary_{arg_strNomeModelo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        plt.savefig(var_strCaminhoSalvar, bbox_inches='tight', dpi=300)
        plt.close()
        
        logger.info(f"Gráfico SHAP salvo em: {var_strCaminhoSalvar}")
        return True
    except ImportError as var_objErro:
        logger.error("Biblioteca 'shap' não instalada. Instale com 'pip install shap'.")
        os.system("pip install shap")
        return gerar_explicabilidade_shap(arg_objModelo, arg_dfXTest, arg_strNomeModelo)
    except Exception as e:
        logger.error(f"Erro ao gerar explicabilidade SHAP: {e}")
        raise e

# ====================================================================================
# 3. Cross-Validation Temporal
# ====================================================================================
def avaliar_cross_validation_temporal(arg_objModelo:object, arg_dfX:pd.DataFrame, arg_serY:pd.Series) -> float:
    """
    Avalia o modelo utilizando particionamento temporal.
    Garante que não haverá vazamento de dados do futuro para o passado.
    Habilitar com ML_EXPERIMENTAL_CV_TEMPORAL=True
    
    Parâmetros:
        arg_objModelo (object): Objeto do modelo treinado.
        arg_dfX (pd.DataFrame): DataFrame com os dados de treinamento.
        arg_serY (pd.Series): Série com os dados de treinamento.
    
    Retorna:
        float: Média F1-Score da Cross-Validation Temporal.
    """
    try:
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.metrics import f1_score
        import numpy as np
        
        logger.info("Executando Cross-Validation Temporal (TimeSeriesSplit)...")
        
        var_objTscv = TimeSeriesSplit(n_splits=5)
        var_listScores = []
        
        for fold, (var_intTrainIndex, var_intTestIndex) in enumerate(var_objTscv.split(arg_dfX)):
            var_dfXTrain, var_dfXTest = arg_dfX.iloc[var_intTrainIndex], arg_dfX.iloc[var_intTestIndex]
            var_serYTrain, var_serYTest = arg_serY.iloc[var_intTrainIndex], arg_serY.iloc[var_intTestIndex]
            
            arg_objModelo.fit(var_dfXTrain, var_serYTrain)
            var_serPreds = arg_objModelo.predict(var_dfXTest)
            var_floatScore = f1_score(var_serYTest, var_serPreds, average='macro')
            var_listScores.append(var_floatScore)
            logger.info(f"Fold {fold+1} - F1-Score Macro: {var_floatScore:.4f}")
            
        var_floatMediaScore = np.mean(var_listScores)
        logger.info(f"Média F1-Score CV Temporal: {var_floatMediaScore:.4f}")
        return var_floatMediaScore
    except Exception as e:
        logger.error(f"Erro ao executar Cross-Validation Temporal: {e}")
        return None

# ====================================================================================
# 4. API REST de Predições (FastAPI)
# ====================================================================================
def iniciar_api_rest():
    """
    Inicializa uma API REST com FastAPI para servir os modelos treinados (_latest.joblib).
    Habilitar com ML_EXPERIMENTAL_FASTAPI=True

    Parâmetros:
        None
    
    Retorna:
        None
    """
    try:
        from fastapi import FastAPI
        import uvicorn
        import joblib
        
        logger.info("Configurando API REST FastAPI...")
        var_objApp = FastAPI(title="Previsor Steam API", description="API de predições de preços do TCC")
        
        # Dicionário em memória para carregar os modelos on-demand
        var_dictModelos = {}
        
        def carregar_modelo(arg_strNomeArquivo:str) -> object:
            """
            Carrega o modelo do arquivo.
            
            Parâmetros:
                arg_strNomeArquivo (str): Nome do arquivo do modelo.
            
            Retorna:
                object: Objeto do modelo carregado.
            """
            try:
                var_strCaminho = os.path.join("prj_TCC_PREVISOR_STEAM", "resources", "models", arg_strNomeArquivo)
                if os.path.exists(var_strCaminho):
                    return joblib.load(var_strCaminho)
                return None
            except Exception as e:
                logger.error(f"Erro ao carregar modelo {arg_strNomeArquivo}: {e}")
                return None

        @var_objApp.get("/")
        def read_root():
            """
            Endpoint raiz da API.
            
            Parâmetros:
                None
            
            Retorna:
                dict: Status da API.
            """
            return {"status": "API Previsor Steam operando normalmente."}
            
        @var_objApp.post("/predict/direcao")
        def predict_direcao(arg_listFeatures: list):
            """
            Endpoint de predição de direção.
            
            Parâmetros:
                arg_listFeatures (list): Lista de features para predição.
            
            Retorna:
                dict: Predição de direção.
            """
            # Carrega o XGBoost latest
            if 'xgb_class' not in var_dictModelos:
                var_dictModelos['xgb_class'] = carregar_modelo("modelo_classificacao_XGBoost_latest.joblib")
                
            if var_dictModelos['xgb_class'] is None:
                return {"error": "Modelo não encontrado"}
                
            # Formata entrada e prediz
            import numpy as np
            var_arrX = np.array(arg_listFeatures).reshape(1, -1)
            var_serPred = var_dictModelos['xgb_class'].predict(var_arrX)
            # Mapeamento reverso simples
            var_dictMapa = {0: "cai", 1: "mantem", 2: "sobe"}
            return {"direcao_prevista": var_dictMapa.get(var_serPred[0], "desconhecido")}

        logger.info("Iniciando servidor Uvicorn na porta 8000...")
        # Isso irá bloquear a thread principal
        uvicorn.run(var_objApp, host="[IP_ADDRESS]", port=8000)
    except ImportError as var_objErro:
        logger.error(f"Erro ao iniciar API REST: {var_objErro}")
        os.system("pip install fastapi uvicorn python-multipart")
        return iniciar_api_rest()
    except Exception as var_objErro:
        logger.error(f"Erro ao iniciar API REST: {var_objErro}")
        raise var_objErro

# ====================================================================================
# 5. Dashboard Streamlit
# ====================================================================================
def iniciar_dashboard_streamlit():
    """
    Gera dinamicamente um arquivo 'dashboard.py' e inicia o servidor do Streamlit.
    Habilitar com ML_EXPERIMENTAL_STREAMLIT=True

    Parâmetros:
        None
    
    Retorna:
        None
    """
    try:
        logger.info("Criando e iniciando Dashboard Streamlit...")
        var_strCaminhoArquivo = "dashboard_tcc_temp.py"
        
        var_strConteudo = '''import streamlit as st
import pandas as pd
import os
import joblib

st.set_page_config(page_title="Previsor Steam - Dashboard", layout="wide")
st.title("📈 Previsor Steam - Dashboard Exploratório")

st.sidebar.header("Carregar Modelo")
caminho_modelo = os.path.join("prj_TCC_PREVISOR_STEAM", "resources", "models", "modelo_classificacao_XGBoost_latest.joblib")

if os.path.exists(caminho_modelo):
    st.sidebar.success("Modelo XGBoost carregado!")
    modelo = joblib.load(caminho_modelo)
    
    st.subheader("Simulador de Predição")
    # Campos de entrada genéricos (exemplo simplificado)
    col1, col2 = st.columns(2)
    review_score = col1.slider("Review Score", 0, 9, 8)
    preco_catalogo = col2.number_input("Preço Catálogo (R$)", 0.0, 500.0, 100.0)
    desconto_medio = col1.number_input("Desconto Médio Janela (%)", 0.0, 90.0, 50.0)
    
    if st.button("Prever Direção de Preço"):
        # Dummy features array matching model input shape
        import numpy as np
        X = np.zeros((1, 13)) # 13 features usadas no normalizar_modelos
        X[0, 0] = review_score
        X[0, 1] = preco_catalogo
        X[0, 8] = desconto_medio
        
        pred = modelo.predict(X)[0]
        mapa = {0: "Cairá", 1: "Manterá", 2: "Subirá"}
        st.success(f"Tendência de preço prevista: **{mapa.get(pred)}**")
else:
    st.sidebar.error("Modelo não encontrado.")
    st.warning("Execute o pipeline de treinamento primeiro.")
'''
        with open(var_strCaminhoArquivo, "w", encoding="utf-8") as f:
            f.write(var_strConteudo)
            
        logger.info("Rodando 'streamlit run dashboard_tcc_temp.py'...")
        os.system(f"streamlit run {var_strCaminhoArquivo}")
    except Exception as e:
        logger.error(f"Erro ao criar/iniciar dashboard Streamlit: {e}")

# ====================================================================================
# 6. Notebook de Análise Exploratória (Geração Automática)
# ====================================================================================
def gerar_notebook_exploratorio():
    """
    Gera um arquivo .ipynb base estruturado para a apresentação do TCC.
    Habilitar com ML_EXPERIMENTAL_NOTEBOOK=True

    Parâmetros:
        None
    
    Retorna:
        None
    """
    try:
        import nbformat as nbf
        
        logger.info("Gerando notebook de análise exploratória...")
        var_objNB = nbf.v4.new_notebook()
        
        var_objNB['cells'] = [
            nbf.v4.new_markdown_cell("# 📊 Análise Exploratória - Previsor Steam TCC\\nEste notebook foi gerado automaticamente."),
            nbf.v4.new_markdown_cell("## 1. Importação de Dados e Bibliotecas"),
            nbf.v4.new_code_cell("import pandas as pd\\nimport matplotlib.pyplot as plt\\nimport seaborn as sns\\nimport json\\n\\n# Ajuste o caminho conforme necessidade\\ncaminho_dados = 'prj_TCC_PREVISOR_STEAM/resources/dados/steam_unificado_complete.json'"),
            nbf.v4.new_markdown_cell("## 2. Carregamento da Base Unificada"),
            nbf.v4.new_code_cell("# df = pd.read_json(caminho_dados)\\n# display(df.head())"),
            nbf.v4.new_markdown_cell("## 3. Distribuição de Preços e Avaliações"),
            nbf.v4.new_code_cell("# sns.histplot(df['preco_numerico'])\\n# plt.show()"),
            nbf.v4.new_markdown_cell("## 4. Análise de Descontos e Temporalidade"),
            nbf.v4.new_code_cell("# Lógica de exploração temporal")
        ]
        
        var_strCaminhoArquivo = "Analise_Exploratoria_TCC.ipynb"
        with open(var_strCaminhoArquivo, 'w', encoding='utf-8') as f:
            nbf.write(var_objNB, f)
            
        logger.info(f"Notebook gerado com sucesso em: {var_strCaminhoArquivo}")
        return True
    except ImportError:
        logger.error("Biblioteca 'nbformat' não instalada. Instale com 'pip install nbformat'.")
        return False
    except Exception as var_objErro:
        logger.error(f"Erro ao gerar notebook de análise exploratória: {var_objErro}")
        return False
