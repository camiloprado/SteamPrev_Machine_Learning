# TODO: Implementação de uma classe de End para gerenciar o final da aplicação, implementar o Close aqui.
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings
from prj_TCC_PREVISOR_STEAM.classes.framework.Close import Close

class End:
    """
    Classe responsável por gerenciar o final da aplicação.
    """

    @classmethod
    def execute(cls):
        """
        Finaliza a aplicação de forma segura.

        Retorna:
        - None
        """
        try:
            Close.execute()
        except Exception as e:
            raise Exception(f"Erro ao finalizar a aplicação: {e}")