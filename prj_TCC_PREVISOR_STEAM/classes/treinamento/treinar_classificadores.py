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
            n_estimators=400,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features="sqrt",
            random_state=42,
            n_jobs=-1,
            class_weight="balanced_subsample",
        )
        
        var_objModelo.fit(var_dfXTrainBalanced, var_serYTrainBalanced)
        var_arrPredTrain = var_objModelo.predict(var_dictSplits["X_train"])
        var_arrPredTest = var_objModelo.predict(var_dictSplits["X_test"])

        var_dictMetricas = Metricas._metricas_classificacao(var_dictSplits["y_test"], var_arrPredTest)

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
            "train_size": var_dictSplits["X_train"].shape[0],
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
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            n_estimators=400,
            learning_rate=0.03,
            max_depth=10,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
        )

        from sklearn.utils.class_weight import compute_sample_weight
        var_arrSampleWeights = compute_sample_weight("balanced", var_serYTrainBalanced)
        
        try:
            var_objModelo.fit(
                var_dfXTrainBalanced,
                var_serYTrainBalanced,
                sample_weight=var_arrSampleWeights,
                eval_set=[(var_dictSplits["X_test"], var_dictSplits["y_test"])],
                verbose=False,
                early_stopping_rounds=50,
            )
        except TypeError:
            var_objModelo.fit(var_dfXTrainBalanced, var_serYTrainBalanced, sample_weight=var_arrSampleWeights)

        var_arrPredTrain = var_objModelo.predict(var_dictSplits["X_train"])
        var_arrPredTest = var_objModelo.predict(var_dictSplits["X_test"])

        var_dictMetricas = Metricas._metricas_classificacao(var_dictSplits["y_test"], var_arrPredTest)

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
            "train_size": var_dictSplits["X_train"].shape[0],
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
            objective="multiclass",
            num_class=3,
            n_estimators=400,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            verbose=-1,
            class_weight="balanced",
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
            "train_size": var_dictSplits["X_train"].shape[0],
            "test_size": var_dictSplits["X_test"].shape[0],
        }


