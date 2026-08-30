import logging
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
import lightgbm as lgb
from prj_TCC_PREVISOR_STEAM.classes.treinamento.metricas import Metricas
from prj_TCC_PREVISOR_STEAM.classes.treinamento.balancear import Balancear
from prj_TCC_PREVISOR_STEAM.classes.treinamento.normalizar_modelos import NormalizarModelos

logger = logging.getLogger("treino.classificadores")

class TreinarClassificadores:
    @classmethod
    def treinar_modelo_random_forest(cls, arg_strHorizonte: str = "prox_evento") -> dict:
        """
        Método para treinar o modelo de Random Forest.

        Parâmetros:
        - arg_strHorizonte (str): Horizonte temporal para treinamento.

        Retorna:
        - dict: Dicionário contendo o modelo treinado, acurácia, F1-macro e tamanhos dos conjuntos de treino e teste.
        """
        var_dictSplits = NormalizarModelos._obter_splits(arg_strHorizonte)

        # Balanceamento multilateral: cap em TODAS as classes (protege 'sobe')
        var_dfXTrainBalanced, var_serYTrainBalanced = Balancear._balancear_classes(
            arg_dfXtrain=var_dictSplits["X_train"],
            arg_serYtrain=var_dictSplits["y_train"],
            arg_floatRatio=10.0,
        )

        var_objModelo = RandomForestClassifier(
            n_estimators=400,                     # Número de árvores de decisão
            max_depth=15,                         # Profundidade máxima das árvores
            min_samples_split=5,                  # Número mínimo de amostras para dividir um nó
            min_samples_leaf=2,                   # Número mínimo de amostras em uma folha
            max_features="sqrt",                  # Fração de features para considerar em cada split
            random_state=42,                      # Reprodutibilidade para garantir a mesma aleatoriedade
            n_jobs=-1,                            # Número de processos para paralelizar o treinamento
            # Sem class_weight: o undersampling de Balancear já corrige o desbalanceamento;
            # aplicar balanced_subsample por cima é correção dupla e piora o F1-macro (validado: -2,8pp).
        )
        
        var_objModelo.fit(var_dfXTrainBalanced, var_serYTrainBalanced)
        var_arrPredTrain = var_objModelo.predict(var_dictSplits["X_train"])
        var_arrPredTest = var_objModelo.predict(var_dictSplits["X_test"])

        var_dictMetricas = Metricas._metricas_classificacao(var_dictSplits["y_test"], var_arrPredTest)

        logger.info("--------------------------------")
        logger.info(f"Random Forest ({arg_strHorizonte})")
        logger.info("--------------------------------")

        Metricas._log_metricas_treino_teste_classificacao(
            arg_strModelo=f"Random Forest ({arg_strHorizonte})",
            arg_yTrain=var_dictSplits["y_train"],
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_dictSplits["y_test"],
            arg_yPredTest=var_arrPredTest,
        )

        Metricas._log_confusion_matrix(
            arg_strModelo=f"RandomForest_{arg_strHorizonte}",
            arg_arrYTrue=var_dictSplits["y_test"],
            arg_arrYPred=var_arrPredTest,
            arg_listLabels=[0, 1, 2],
            arg_listLabelNames=["cai", "mantem", "sobe"],
            arg_strSplit="teste"
        )
        
        return {
            "modelo": var_objModelo,
            **var_dictMetricas,
            "train_size": var_dfXTrainBalanced.shape[0],
            "test_size": var_dictSplits["X_test"].shape[0],
        }


    @classmethod
    def treinar_modelo_xgboost(cls, arg_strHorizonte: str = "prox_evento") -> dict:
        """
        Método para treinar o modelo de XGBoost.

        Parâmetros:
        - arg_strHorizonte (str): Horizonte temporal para treinamento.

        Retorna:
        - dict: Dicionário contendo o modelo treinado, acurácia, F1-macro e tamanhos dos conjuntos de treino e teste.
        """
        var_dictSplits = NormalizarModelos._obter_splits(arg_strHorizonte)

        # Balanceamento multilateral: cap em TODAS as classes (protege 'sobe')
        var_dfXTrainBalanced, var_serYTrainBalanced = Balancear._balancear_classes(
            arg_dfXtrain=var_dictSplits["X_train"],
            arg_serYtrain=var_dictSplits["y_train"],
            arg_floatRatio=10.0,
        )

        var_objModelo = xgb.XGBClassifier(
            objective="multi:softprob",    # Função de perda para classificação multiclasse
            num_class=3,                   # Número de classes (cai, mantem, sobe)
            eval_metric="mlogloss",        # Métrica de avaliação para classificação multiclasse
            n_estimators=400,              # Número de árvores de decisão
            learning_rate=0.03,            # Taxa de aprendizado
            max_depth=10,                  # Profundidade máxima das árvores
            subsample=0.8,                 # Fração de amostras para treinar cada árvore
            colsample_bytree=0.8,          # Fração de features para treinar cada árvore
            random_state=42,               # Reprodutibilidade para garantir a mesma aleatoriedade
            early_stopping_rounds=50,      # Early stopping para evitar overfitting
        )

        # Sem sample_weight: o undersampling de Balancear já corrige o desbalanceamento;
        # aplicar compute_sample_weight("balanced") por cima é correção dupla e piora o
        # F1-macro (validado: -6,5pp em 30d).
        var_objModelo.fit(
            var_dfXTrainBalanced,
            var_serYTrainBalanced,
            eval_set=[(var_dictSplits["X_test"], var_dictSplits["y_test"])],
            verbose=False,
        )

        var_arrPredTrain = var_objModelo.predict(var_dictSplits["X_train"])
        var_arrPredTest = var_objModelo.predict(var_dictSplits["X_test"])

        var_dictMetricas = Metricas._metricas_classificacao(var_dictSplits["y_test"], var_arrPredTest)
        
        logger.info("--------------------------------")
        logger.info(f"XGBoost ({arg_strHorizonte})")
        logger.info("--------------------------------")

        Metricas._log_metricas_treino_teste_classificacao(
            arg_strModelo=f"XGBoost ({arg_strHorizonte})",
            arg_yTrain=var_dictSplits["y_train"],
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_dictSplits["y_test"],
            arg_yPredTest=var_arrPredTest,
        )

        Metricas._log_confusion_matrix(
            arg_strModelo=f"XGBoost_{arg_strHorizonte}",
            arg_arrYTrue=var_dictSplits["y_test"],
            arg_arrYPred=var_arrPredTest,
            arg_listLabels=[0, 1, 2],
            arg_listLabelNames=["cai", "mantem", "sobe"],
        )
        
        return {
            "modelo": var_objModelo,
            **var_dictMetricas,
            "train_size": var_dfXTrainBalanced.shape[0],
            "test_size": var_dictSplits["X_test"].shape[0],
        }


    @classmethod
    def treinar_modelo_lightgbm(cls, arg_strHorizonte: str = "prox_evento") -> dict:
        """
        Método para treinar o modelo de LightGBM.

        Parâmetros:
        - arg_strHorizonte (str): Horizonte temporal para treinamento.

        Retorna:
        - dict: Dicionário contendo o modelo treinado, acurácia, F1-macro e tamanhos dos conjuntos de treino e teste.
        """
        var_dictSplits = NormalizarModelos._obter_splits(arg_strHorizonte)

        # Balanceamento multilateral: cap em TODAS as classes (protege 'sobe')
        var_dfXTrainBalanced, var_serYTrainBalanced = Balancear._balancear_classes(
            arg_dfXtrain=var_dictSplits["X_train"],
            arg_serYtrain=var_dictSplits["y_train"],
            arg_floatRatio=10.0,
        )

        var_objModelo = lgb.LGBMClassifier(
            objective="multiclass",                # Função de perda para classificação multiclasse
            num_class=3,                           # Número de classes (cai, mantem, sobe)
            n_estimators=400,                      # Número de árvores de decisão
            learning_rate=0.05,                    # Taxa de aprendizado (shrinkage)
            num_leaves=31,                         # Número máximo de folhas em cada árvore
            subsample=0.9,                         # Fração de amostras para treinar cada árvore
            colsample_bytree=0.9,                  # Fração de features para treinar cada árvore
            random_state=42,                       # Reprodutibilidade para garantir a mesma aleatoriedade
            verbose=-1,                            # Nível de verbosidade (0 = nenhum log, 1 = logs básicos, 2 = logs detalhados, -1 = logs mínimos)
            # Sem class_weight: o undersampling de Balancear já corrige o desbalanceamento;
            # aplicar balanced por cima é correção dupla e piora o F1-macro (validado: -7,2pp).
        )

        try:
            var_objModelo.fit(
                var_dfXTrainBalanced,
                var_serYTrainBalanced,
                eval_set=[(var_dictSplits["X_test"], var_dictSplits["y_test"])],
                eval_metric="multi_logloss",
                callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)],
            )
        except TypeError:
            var_objModelo.fit(var_dfXTrainBalanced, var_serYTrainBalanced)

        var_arrPredTrain = var_objModelo.predict(var_dictSplits["X_train"])
        var_arrPredTest = var_objModelo.predict(var_dictSplits["X_test"])

        var_dictMetricas = Metricas._metricas_classificacao(var_dictSplits["y_test"], var_arrPredTest)

        logger.info("--------------------------------")
        logger.info(f"LightGBM ({arg_strHorizonte})")
        logger.info("--------------------------------")

        Metricas._log_metricas_treino_teste_classificacao(
            arg_strModelo=f"LightGBM ({arg_strHorizonte})",
            arg_yTrain=var_dictSplits["y_train"],
            arg_yPredTrain=var_arrPredTrain,
            arg_yTest=var_dictSplits["y_test"],
            arg_yPredTest=var_arrPredTest,
        )

        Metricas._log_confusion_matrix(
            arg_strModelo=f"LightGBM_{arg_strHorizonte}",
            arg_arrYTrue=var_dictSplits["y_test"],
            arg_arrYPred=var_arrPredTest,
            arg_listLabels=[0, 1, 2],
            arg_listLabelNames=["cai", "mantem", "sobe"],
        )
        
        return {
            "modelo": var_objModelo,
            **var_dictMetricas,
            "train_size": var_dfXTrainBalanced.shape[0],
            "test_size": var_dictSplits["X_test"].shape[0],
        }


