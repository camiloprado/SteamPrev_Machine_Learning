from prj_TCC_PREVISOR_STEAM.classes.tests.test_treinamento import Treinamento_Teste as tt

from sklearn.model_selection import train_test_split
from sklearn.model_selection import StratifiedShuffleSplit
from pandas.plotting import scatter_matrix
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class ConjuntodeTeste:
    """
    Classe para representar um conjunto de teste para o treinamento do modelo.
    """
    var_DadosEntrada = "" #TODO: Carregar dados de entrada da tabela unificada de steam_unificado e itad_raw
    train_set, test_set = tt.split_train_test(var_DadosEntrada, test_ratio=0.2)
    len(train_set)
    len(test_set)

    split = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    for train_index, test_index in split.split(var_DadosEntrada, var_DadosEntrada["target"]):
        strat_train_set = var_DadosEntrada.loc[train_index]
        strat_test_set = var_DadosEntrada.loc[test_index]
    
    for set_ in (strat_train_set, strat_test_set):
        set_.drop("target", axis=1, inplace=True)

    target = strat_train_set["target"].copy()
    target.plot(kind="scatter", x="feature1", y="feature2")  # Substitua feature1 e feature2 pelos nomes reais das colunas
    target.plot(kind="scatter", x="feature1", y="feature2", alpha=0.1)  # Substitua feature1 e feature2 pelos nomes reais das colunas
    target.plot(kind="scatter", x="feature1", y="feature2", alpha=0.4,
                s=target["col1"]/100, label="Label", figsize=(10,7), 
                c="median", cmap=plt.get_cmap("jet"), colorbar=True,)  # Substitua feature1 e feature2 pelos nomes reais das colunas
    plt.legend()
    corr_matrix = target.corr()
    print(corr_matrix["target"].sort_values(ascending=False))
    attributes = ["feature1", "feature2", "feature3"]  # Substitua pelos nomes reais das colunas
    scatter_matrix(target[attributes], figsize=(12, 8))