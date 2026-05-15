"""
Este arquivo contém as implementações para o "Backlog TCC - Melhorias Futuras".
As funções aqui definidas são experimentais e podem ser habilitadas posteriormente
através do arquivo .env.

Dependências adicionais requeridas para uso completo:
pip install optuna shap fastapi uvicorn streamlit jupyter nbformat
"""

import os
import logging
from datetime import datetime

logger = logging.getLogger("treino.experimentos")

# ====================================================================================
# 1. Hyperparameter Tuning (Optuna / GridSearch para XGBoost)
# ====================================================================================
def otimizar_hiperparametros_xgboost(arg_dfX_train, arg_serY_train):
    """
    Otimiza os hiperparâmetros do modelo XGBoost utilizando a biblioteca Optuna.
    Habilitar com ML_EXPERIMENTAL_OPTUNA=True
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
            param = {
                'verbosity': 0,
                'objective': 'multi:softprob',
                'num_class': 3,
                'max_depth': trial.suggest_int('max_depth', 3, 12),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'n_estimators': trial.suggest_int('n_estimators', 100, 500),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0)
            }
            
            modelo = xgb.XGBClassifier(**param, random_state=42)
            modelo.fit(X_tr, y_tr)
            preds = modelo.predict(X_val)
            return f1_score(y_val, preds, average='macro')
            
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=20) # 20 trials para demonstração
        
        logger.info(f"Melhores hiperparâmetros encontrados: {study.best_params}")
        return study.best_params
    except ImportError:
        logger.error("Biblioteca 'optuna' ou 'xgboost' não instalada. Instale com 'pip install optuna xgboost'.")
        return None

# ====================================================================================
# 2. SHAP Values (Explicabilidade dos modelos)
# ====================================================================================
def gerar_explicabilidade_shap(arg_modelo, arg_dfX_test, arg_strNomeModelo="XGBoost"):
    """
    Gera gráficos de importância de features utilizando SHAP Values.
    Habilitar com ML_EXPERIMENTAL_SHAP=True
    """
    try:
        import shap
        import matplotlib.pyplot as plt
        import pandas as pd
        
        logger.info(f"Gerando explicabilidade SHAP para o modelo {arg_strNomeModelo}...")
        
        # O ideal é usar uma amostra menor (ex: 5000) para calcular SHAP mais rápido
        X_sample = arg_dfX_test.sample(min(5000, len(arg_dfX_test)), random_state=42) if isinstance(arg_dfX_test, pd.DataFrame) else arg_dfX_test[:5000]
        
        # Explainer Tree (funciona para XGBoost, LightGBM, RandomForest)
        explainer = shap.TreeExplainer(arg_modelo)
        shap_values = explainer.shap_values(X_sample)
        
        # Gera o Summary Plot
        plt.figure(figsize=(10, 6))
        shap.summary_plot(shap_values, X_sample, show=False)
        
        caminho_salvar = os.path.join("prj_TCC_PREVISOR_STEAM", "resources", "relatorios", f"shap_summary_{arg_strNomeModelo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        plt.savefig(caminho_salvar, bbox_inches='tight', dpi=300)
        plt.close()
        
        logger.info(f"Gráfico SHAP salvo em: {caminho_salvar}")
        return True
    except ImportError:
        logger.error("Biblioteca 'shap' não instalada. Instale com 'pip install shap'.")
        return False

# ====================================================================================
# 3. Cross-Validation Temporal
# ====================================================================================
def avaliar_cross_validation_temporal(arg_modelo, arg_dfX, arg_serY):
    """
    Avalia o modelo utilizando particionamento temporal.
    Garante que não haverá vazamento de dados do futuro para o passado.
    Habilitar com ML_EXPERIMENTAL_CV_TEMPORAL=True
    """
    try:
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.metrics import f1_score
        import numpy as np
        
        logger.info("Executando Cross-Validation Temporal (TimeSeriesSplit)...")
        
        tscv = TimeSeriesSplit(n_splits=5)
        scores = []
        
        for fold, (train_index, test_index) in enumerate(tscv.split(arg_dfX)):
            X_train, X_test = arg_dfX.iloc[train_index], arg_dfX.iloc[test_index]
            y_train, y_test = arg_serY.iloc[train_index], arg_serY.iloc[test_index]
            
            arg_modelo.fit(X_train, y_train)
            preds = arg_modelo.predict(X_test)
            score = f1_score(y_test, preds, average='macro')
            scores.append(score)
            logger.info(f"Fold {fold+1} - F1-Score Macro: {score:.4f}")
            
        media_score = np.mean(scores)
        logger.info(f"Média F1-Score CV Temporal: {media_score:.4f}")
        return media_score
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
    """
    try:
        from fastapi import FastAPI
        import uvicorn
        import joblib
        
        logger.info("Configurando API REST FastAPI...")
        app = FastAPI(title="Previsor Steam API", description="API de predições de preços do TCC")
        
        # Dicionário em memória para carregar os modelos on-demand
        modelos = {}
        
        def carregar_modelo(nome_arquivo):
            caminho = os.path.join("prj_TCC_PREVISOR_STEAM", "resources", "models", nome_arquivo)
            if os.path.exists(caminho):
                return joblib.load(caminho)
            return None

        @app.get("/")
        def read_root():
            return {"status": "API Previsor Steam operando normalmente."}
            
        @app.post("/predict/direcao")
        def predict_direcao(features: list):
            # Carrega o XGBoost latest
            if 'xgb_class' not in modelos:
                modelos['xgb_class'] = carregar_modelo("modelo_classificacao_XGBoost_latest.joblib")
                
            if modelos['xgb_class'] is None:
                return {"error": "Modelo não encontrado"}
                
            # Formata entrada e prediz
            import numpy as np
            X = np.array(features).reshape(1, -1)
            pred = modelos['xgb_class'].predict(X)
            # Mapeamento reverso simples
            mapa = {0: "cai", 1: "mantem", 2: "sobe"}
            return {"direcao_prevista": mapa.get(pred[0], "desconhecido")}

        logger.info("Iniciando servidor Uvicorn na porta 8000...")
        # Isso irá bloquear a thread principal
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except ImportError:
        logger.error("Bibliotecas 'fastapi' ou 'uvicorn' não instaladas.")

# ====================================================================================
# 5. Dashboard Streamlit
# ====================================================================================
def iniciar_dashboard_streamlit():
    """
    Gera dinamicamente um arquivo 'dashboard.py' e inicia o servidor do Streamlit.
    Habilitar com ML_EXPERIMENTAL_STREAMLIT=True
    """
    try:
        logger.info("Criando e iniciando Dashboard Streamlit...")
        dash_path = "dashboard_tcc_temp.py"
        
        conteudo = '''import streamlit as st
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
        with open(dash_path, "w", encoding="utf-8") as f:
            f.write(conteudo)
            
        logger.info("Rodando 'streamlit run dashboard_tcc_temp.py'...")
        os.system(f"streamlit run {dash_path}")
    except Exception as e:
        logger.error(f"Erro ao criar/iniciar dashboard Streamlit: {e}")

# ====================================================================================
# 6. Notebook de Análise Exploratória (Geração Automática)
# ====================================================================================
def gerar_notebook_exploratorio():
    """
    Gera um arquivo .ipynb base estruturado para a apresentação do TCC.
    Habilitar com ML_EXPERIMENTAL_NOTEBOOK=True
    """
    try:
        import nbformat as nbf
        
        logger.info("Gerando notebook de análise exploratória...")
        nb = nbf.v4.new_notebook()
        
        nb['cells'] = [
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
        
        caminho_ipynb = "Analise_Exploratoria_TCC.ipynb"
        with open(caminho_ipynb, 'w', encoding='utf-8') as f:
            nbf.write(nb, f)
            
        logger.info(f"Notebook gerado com sucesso em: {caminho_ipynb}")
        return True
    except ImportError:
        logger.error("Biblioteca 'nbformat' não instalada. Instale com 'pip install nbformat'.")
        return False
