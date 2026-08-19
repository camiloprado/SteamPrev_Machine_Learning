import logging
import pandas as pd

logger = logging.getLogger("treino.balancear")

class Balancear:
    @classmethod
    def _balancear_classes(cls, arg_dfXtrain: pd.DataFrame, arg_serYtrain: pd.Series, arg_floatRatio: float = 10.0) -> tuple:
        """
        Realiza undersampling MULTILATERAL no treino usando pandas.

        Aplica um teto a TODAS as classes cujo volume supere 'ratio' vezes
        o tamanho da MENOR classe (normalmente "sobe"), não apenas à classe
        majoritária. Isso protege as classes raras de serem sufocadas mesmo
        quando não há dominância extrema de um único rótulo.

        Exemplo com ratio=10 e 30d {cai=554k, mantem=582k, sobe=16k}:
          limite = 16k × 10 = 160k
          cai  → amostrado para 160k (antes: 554k)
          mantem → amostrado para 160k (antes: 582k)
          sobe → mantida em 16k (< limite)

        Parâmetros:
        - arg_dfXtrain (pd.DataFrame): Features de treino.
        - arg_serYtrain (pd.Series): Alvo de treino.
        - arg_floatRatio (float): Limite máximo em múltiplos da menor classe.

        Retorna:
        - tuple: (X_train_bal, y_train_bal)
        """
        var_serContagens = arg_serYtrain.value_counts()
        if len(var_serContagens) < 2:
            return arg_dfXtrain, arg_serYtrain

        # Limite baseado na MENOR classe (protege a classe "sobe" por padrão)
        var_intMenor = int(var_serContagens.min())
        var_intLimite = int(var_intMenor * arg_floatRatio)

        # Se nenhuma classe ultrapassa o limite, não há necessidade de balancear
        if int(var_serContagens.max()) <= var_intLimite:
            return arg_dfXtrain, arg_serYtrain

        # Aplica undersampling a CADA classe que ultrapasse o limite
        var_listPartes = []
        for var_typeClasse, var_intContagem in var_serContagens.items():
            var_maskClasse = arg_serYtrain == var_typeClasse
            var_dfClasseX = arg_dfXtrain[var_maskClasse]
            var_serClasseY = arg_serYtrain[var_maskClasse]

            if var_intContagem > var_intLimite:
                # Reduz esta classe ao limite máximo
                var_dfClasseX = var_dfClasseX.sample(n=var_intLimite, random_state=42)
                var_serClasseY = var_serClasseY.loc[var_dfClasseX.index]

            var_listPartes.append((var_dfClasseX, var_serClasseY))

        var_dfXTrainBalanced = pd.concat([var_parX for var_parX, _ in var_listPartes])
        var_serYTrainBalanced = pd.concat([var_parY for _, var_parY in var_listPartes])

        # Embaralha para misturar as classes no dataset resultante
        var_dfXTrainBalanced = var_dfXTrainBalanced.sample(frac=1.0, random_state=42)
        var_serYTrainBalanced = var_serYTrainBalanced.loc[var_dfXTrainBalanced.index]

        logger.info(
            f"Balanceamento multilateral (ratio={arg_floatRatio}, limite={var_intLimite:,}): "
            f"{var_serContagens.to_dict()} -> {var_serYTrainBalanced.value_counts().to_dict()}"
        )

        return var_dfXTrainBalanced, var_serYTrainBalanced


