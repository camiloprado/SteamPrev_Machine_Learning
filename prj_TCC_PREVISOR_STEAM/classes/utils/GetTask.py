class GetTask:
    """
    Classe utilitária para gerenciar as tarefas.
    """
    @classmethod
    def __init__(cls):
        cls.var_listTaskQueue = []

    @classmethod
    def criar_fila(cls):
        """
        Cria a fila de tarefas.
        
        Retorna:
        """
        cls.var_listTaskQueue.append()

    @classmethod
    def abandona_fila(cls, arg_boolAbandonar: bool = True):
        """
        Abandona a fila de tarefas.

        Retorna:
        - None
        """
        if arg_boolAbandonar:
            if len(cls.var_listTaskQueue) > 0:
                for var_intIndex in range(len(cls.var_listTaskQueue)):
                    cls.var_listTaskQueue.pop(var_intIndex)

    @classmethod
    def load_task_queue(cls):
        """
        Carrega a fila de tarefas.

        Retorna:
        - None
        """
        pass