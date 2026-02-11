from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.treinamento.treinamento import TreinarModelo
from prj_TCC_PREVISOR_STEAM.aprendizadodemaquina_livro.treinamento_avaliacao import TreinamentoAvaliacao

class ProcessadorTreinamento:
    """
    Classe responsável pelo processamento do treinamento do modelo de machine learning.
    """

    @classmethod
    def executar_treinamento(cls):
        """
        Executa o processo de treinamento do modelo de machine learning.
        
        Retorna:
        - None
        """
        # Carrega os dados de treinamento
        var_dfXTreino, var_serYtreino, var_dfXTeste, var_serYteste = TreinarModelo.carregar_dados_treinamento()
        
        # Treina o modelo
        var_modelo = TreinamentoAvaliacao.metodo_treinarModeloRegressaoLinear(var_dfXTreino, var_serYtreino)
        
        # Avalia o modelo
        var_r2 = TreinamentoAvaliacao.metodo_avaliarModeloRegressaoLinear(var_dfXTeste, var_serYteste)
        
        print(f"Modelo treinado com R²: {var_r2}")