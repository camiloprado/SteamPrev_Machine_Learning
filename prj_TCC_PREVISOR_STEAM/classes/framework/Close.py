#TODO: Implementação de uma classe de Close para gerenciar o fechamento da aplicação.
from prj_TCC_PREVISOR_STEAM.classes.framework.AllSettings import Settings

class Close:
    """
    Classe para gerenciar o fechamento da aplicação.
    """
    @classmethod
    def execute(cls):
        """
        Fecha as aplicações de forma segura.
        
        Retorna:
        - None
        """
        for var_intTentativa in range(Settings._var_dictSettings["max_tentativas"]):
            try:
                # Lógica para fechar a aplicação
                pass
            except Exception as e:
                if var_intTentativa == Settings._var_dictSettings["max_tentativas"] - 1:
                    raise e
                else: continue
            else:
                break